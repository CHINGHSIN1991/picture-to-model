import { chromium } from '@playwright/test'
import { mkdir, writeFile, readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'

// Step 10 evidence: hero / full-page / mobile screenshots of the landing page with the
// installed Chrome and its real GPU, plus a short frame-rate sample and console errors.
// LANDING_STATES=1,2,3 also captures `?state=N` previews of other section states.
const baseUrl = process.env.VIEWER_URL ?? 'http://127.0.0.1:5173'
const output = new URL('../screenshots/', import.meta.url)
const sections = ['hero', 'upload', 'model', 'controls', 'interaction', 'cta']
const states = (process.env.LANDING_STATES ?? '').split(',').filter(Boolean).map(Number)
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome', headless: process.env.VIEWER_HEADED !== '1' })
const errors = []
const hook = (page) => {
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()) })
}
const ready = (page) => page.locator('.site[data-state="ready"]').waitFor({ timeout: 30_000 })
const file = (name) => new URL(name, output).pathname
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 })
  hook(page)
  await page.goto(baseUrl)
  await ready(page)
  await page.waitForTimeout(1500)
  const performance = await page.evaluate(async () => {
    const canvas = document.querySelector('.stage canvas')
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
        if (time - start < 5000) requestAnimationFrame(measure)
        else resolve(values)
      }
      requestAnimationFrame(measure)
    })
    const sorted = [...intervals].sort((a, b) => a - b)
    const total = intervals.reduce((a, b) => a + b, 0)
    return {
      renderer, viewport: [innerWidth, innerHeight], buffer: [canvas.width, canvas.height], devicePixelRatio,
      canvasPosition: getComputedStyle(canvas.parentElement).position, pointerEvents: getComputedStyle(canvas.parentElement).pointerEvents,
      pageHeight: document.documentElement.scrollHeight,
      frames: intervals.length, durationMs: total, averageFps: 1000 / (total / intervals.length),
      medianFrameMs: sorted[Math.floor(sorted.length * 0.5)], p95FrameMs: sorted[Math.floor(sorted.length * 0.95)],
    }
  })
  await page.screenshot({ path: file('landing-hero.png') })
  await page.screenshot({ path: file('landing-full.png'), fullPage: true })
  for (const state of states) {
    await page.goto(`${baseUrl}/?state=${state}`)
    await ready(page)
    await page.locator(`#${sections[state - 1]}`).scrollIntoViewIfNeeded()
    await page.waitForTimeout(600)
    await page.screenshot({ path: file(`landing-state-${state}.png`) })
  }
  await page.close()
  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 })
  hook(mobile)
  await mobile.goto(baseUrl)
  await ready(mobile)
  await mobile.waitForTimeout(600)
  await mobile.screenshot({ path: file('landing-mobile.png') })
  const scrollWidth = await mobile.evaluate(() => document.documentElement.scrollWidth)
  await mobile.close()
  const hash = async (path) => createHash('sha256').update(await readFile(path)).digest('hex')
  const report = {
    measuredAt: new Date().toISOString(), baseUrl, browser: browser.version(),
    method: '5-second requestAnimationFrame sample after 1.5-second warmup at the hero; default browser GPU selection',
    performance, hardwareRenderer: !/swiftshader|llvmpipe|software/i.test(performance.renderer),
    mobile: { viewport: [390, 844], scrollWidth },
    glbSha256: await hash(new URL('../../export/reef.glb', import.meta.url)),
    sectionsSha256: await hash(new URL('../src/three/config/sections.ts', import.meta.url)),
    errors, screenshots: {},
  }
  for (const name of ['landing-hero.png', 'landing-full.png', 'landing-mobile.png']) report.screenshots[name] = await hash(file(name))
  await writeFile(new URL('landing-report.json', output), `${JSON.stringify(report, null, 2)}\n`)
  console.log(JSON.stringify(report, null, 2))
  if (errors.length) process.exitCode = 1
} finally {
  await browser.close()
}
