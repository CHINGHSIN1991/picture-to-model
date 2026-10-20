import { chromium } from '@playwright/test'
import { mkdir, writeFile, readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'

// Run against `bun run dev` or `bun run preview`; never force software rendering.
const baseUrl = process.env.VIEWER_URL ?? 'http://127.0.0.1:5173'
const output = new URL('../screenshots/', import.meta.url)
await mkdir(output, { recursive: true })
const browser = await chromium.launch({
  channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome',
  headless: process.env.VIEWER_HEADED !== '1',
})
const errors = []
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 })
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
  })
  await page.goto(`${baseUrl}/?debug`)
  await page.locator('main[data-state="ready"]').waitFor()
  await page.waitForTimeout(2000)
  const performance = await page.evaluate(async () => {
    const canvas = document.querySelector('.viewport canvas')
    const gl = canvas.getContext('webgl2')
    const extension = gl.getExtension('WEBGL_debug_renderer_info')
    const renderer = extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)
    const intervals = await new Promise((resolve) => {
      const values = []
      let start, previous
      function measure(time) {
        if (start === undefined) start = time
        if (previous !== undefined) values.push(time - previous)
        previous = time
        if (time - start < 10000) requestAnimationFrame(measure)
        else resolve(values)
      }
      requestAnimationFrame(measure)
    })
    const sorted = [...intervals].sort((a, b) => a - b)
    return {
      renderer, userAgent: navigator.userAgent,
      viewport: [innerWidth, innerHeight], buffer: [canvas.width, canvas.height],
      devicePixelRatio, debugAndStatsEnabled: true, animated: true,
      frames: intervals.length, durationMs: intervals.reduce((a, b) => a + b, 0),
      averageFps: 1000 / (intervals.reduce((a, b) => a + b, 0) / intervals.length),
      medianFrameMs: sorted[Math.floor(sorted.length * 0.5)],
      p95FrameMs: sorted[Math.floor(sorted.length * 0.95)],
      framesOver25Ms: intervals.filter((value) => value > 25).length,
    }
  })
  await page.screenshot({ path: new URL('lighting-debug.png', output).pathname })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.setViewportSize({ width: 1024, height: 768 })
  await page.goto(baseUrl)
  await page.locator('main[data-state="ready"]').waitFor()
  await page.screenshot({ path: new URL('lighting-v1.png', output).pathname })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: new URL('lighting-mobile.png', output).pathname })
  const hash = async (path) => createHash('sha256').update(await readFile(path)).digest('hex')
  const report = {
    measuredAt: new Date().toISOString(),
    baseUrl,
    browser: browser.version(),
    headless: process.env.VIEWER_HEADED !== '1',
    method: '10-second requestAnimationFrame sample after 2-second warmup, with GUI/stats and animated lighting; default browser GPU selection',
    performance,
    hardwareRenderer: !/swiftshader|llvmpipe|software/i.test(performance.renderer),
    glbSha256: await hash(new URL('../../export/reef.glb', import.meta.url)),
    configSha256: await hash(new URL('../src/three/lightingConfig.ts', import.meta.url)),
    errors,
    screenshots: {},
  }
  for (const file of ['lighting-v1.png', 'lighting-mobile.png', 'lighting-debug.png']) {
    report.screenshots[file] = await hash(new URL(file, output))
  }
  await writeFile(new URL('lighting-report.json', output), `${JSON.stringify(report, null, 2)}\n`)
  console.log(JSON.stringify(report, null, 2))
  if (errors.length) process.exitCode = 1
} finally {
  await browser.close()
}
