import { chromium } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'

const baseUrl = process.env.VIEWER_URL ?? 'http://127.0.0.1:5173'
const output = new URL('../screenshots/', import.meta.url)
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome' })
const errors = []
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 })
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()) })
  await page.goto(baseUrl)
  await page.locator('.site[data-state="ready"]').waitFor()
  await page.waitForTimeout(1000)
  const screenshots = []
  for (const [name, x, y] of [
    ['neutral', 720, 450], ['top-left', 0, 0], ['top-right', 1439, 0],
    ['bottom-right', 1439, 899], ['bottom-left', 0, 899],
  ]) {
    await page.mouse.move(x, y)
    await page.waitForTimeout(1200)
    const filename = `pointer-${name}.png`
    await page.screenshot({ path: new URL(filename, output).pathname })
    screenshots.push(filename)
  }
  await page.evaluate(() => window.dispatchEvent(new PointerEvent('pointerout', { relatedTarget: null })))
  await page.waitForTimeout(2500)
  await page.screenshot({ path: new URL('pointer-returned.png', output).pathname })
  screenshots.push('pointer-returned.png')
  // Keep the model moving during sampling, including shadow refreshes.
  const performance = await page.evaluate(async () => {
    const canvas = document.querySelector('canvas')
    const gl = canvas.getContext('webgl2')
    const extension = gl.getExtension('WEBGL_debug_renderer_info')
    const renderer = extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)
    const intervals = await new Promise((resolve) => {
      const values = []
      let start, previous
      function frame(time) {
        start ??= time
        if (previous !== undefined) values.push(time - previous)
        previous = time
        window.dispatchEvent(new PointerEvent('pointermove', {
          pointerType: 'mouse', clientX: (0.5 + Math.sin(time / 400) * 0.48) * innerWidth,
          clientY: (0.5 + Math.cos(time / 600) * 0.48) * innerHeight,
        }))
        if (time - start < 5000) requestAnimationFrame(frame)
        else resolve(values)
      }
      requestAnimationFrame(frame)
    })
    const sorted = [...intervals].sort((a, b) => a - b)
    return {
      renderer, viewport: [innerWidth, innerHeight], buffer: [canvas.width, canvas.height],
      frames: intervals.length, averageFps: 1000 * intervals.length / intervals.reduce((a, b) => a + b, 0),
      p95FrameMs: sorted[Math.floor(sorted.length * 0.95)],
    }
  })
  const report = {
    measuredAt: new Date().toISOString(), browser: browser.version(), baseUrl,
    method: '5-second RAF sample while synthetic mouse input continuously tilts the model; water animation and shadow updates enabled; default GPU',
    performance, screenshots, errors,
  }
  await writeFile(new URL('pointer-report.json', output), `${JSON.stringify(report, null, 2)}\n`)
  console.log(JSON.stringify(report, null, 2))
  if (errors.length) process.exitCode = 1
} finally {
  await browser.close()
}
