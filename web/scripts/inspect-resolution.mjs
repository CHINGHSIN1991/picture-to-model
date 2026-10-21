// Step 16: Chrome device-metrics emulation; CSS size stays fixed during DPR changes.
import { chromium } from '@playwright/test'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import assert from 'node:assert/strict'

const baseUrl = process.env.VIEWER_URL ?? 'http://127.0.0.1:5173'
const output = new URL('../screenshots/', import.meta.url)
const file = (name) => new URL(name, output).pathname
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome' })
const errors = [], samples = []
try {
  for (const entry of [
    { name: 'landing', url: '/?mode=live', ready: '.site' },
    { name: 'viewer', url: '/viewer.html', ready: 'main' },
  ]) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, reducedMotion: 'reduce' })
    const page = await context.newPage()
    page.on('pageerror', (error) => errors.push(`${entry.name}: ${error.message}`))
    await page.goto(`${baseUrl}${entry.url}`)
    await page.locator(`${entry.ready}[data-state="ready"]`).waitFor()
    const cdp = await context.newCDPSession(page)
    let media = ''
    for (const dpr of [2, 3, 1, 1.25, 0.75, 2]) {
      await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: dpr, mobile: false })
      // CDP metrics need a media override change to invalidate resolution queries.
      media = media ? '' : 'screen'
      await cdp.send('Emulation.setEmulatedMedia', { media, features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] })
      const expectedRatio = Math.min(dpr, 1.5)
      await page.waitForFunction((ratio) => document.querySelector('canvas')?.width === Math.floor(1440 * ratio), expectedRatio)
      const measurement = await page.locator('canvas').evaluate((canvas) => {
        const gl = canvas.getContext('webgl2')
        return { dpr: devicePixelRatio, css: [canvas.clientWidth, canvas.clientHeight], buffer: [canvas.width, canvas.height],
          drawingBuffer: [gl.drawingBufferWidth, gl.drawingBufferHeight], antialias: gl.getContextAttributes().antialias }
      })
      assert.deepEqual(measurement.buffer, [Math.floor(1440 * expectedRatio), Math.floor(900 * expectedRatio)])
      assert.deepEqual(measurement.drawingBuffer, measurement.buffer)
      assert.equal(measurement.antialias, true)
      samples.push({ entry: entry.name, ...measurement, effectiveRatio: expectedRatio,
        pixelReductionVsUncapped: 1 - (measurement.buffer[0] * measurement.buffer[1]) / (1440 * 900 * dpr * dpr) })
      if (dpr === 3 || dpr === 1) {
        await page.waitForTimeout(150)
        await page.screenshot({ path: file(`resolution-${entry.name}-dpr${dpr}.png`), scale: 'css' })
      }
    }
    await context.close()
  }
  assert.deepEqual(errors, [])
  const report = { measuredAt: new Date().toISOString(), browser: browser.version(), baseUrl,
    method: 'Chrome CDP device metrics: DPR 2 → 3 → 1 → 1.25 → 0.75 → 2 at fixed 1440×900 CSS viewport; screen/default media override toggled to invalidate resolution queries; reduced motion freezes water; screenshots at CSS scale. Emulation, not physical monitor movement. Pixel savings describe buffer area, not measured GPU time.',
    config: { maxPixelRatio: 1.5, antialias: true, powerPreference: 'default' }, samples, errors }
  await writeFile(file('resolution-report.json'), `${JSON.stringify(report, null, 2)}\n`)
  const sheet = await browser.newPage({ viewport: { width: 1440, height: 650 } })
  const cards = await Promise.all([
    ['resolution-landing-dpr1.png', 'Landing · DPR 1 · 1440 × 900 buffer'],
    ['resolution-landing-dpr3.png', 'Landing · DPR 3 capped at 1.5 · 2160 × 1350 buffer'],
    ['resolution-viewer-dpr3.png', 'Viewer · DPR 3 capped at 1.5 · 2160 × 1350 buffer'],
  ].map(async ([name, caption]) => `<figure><img src="data:image/png;base64,${(await readFile(file(name))).toString('base64')}"><figcaption>${caption}</figcaption></figure>`))
  const rows = samples.filter((sample) => sample.entry === 'landing').slice(0, 5).map((s) => `<tr><td>${s.dpr}</td><td>${s.effectiveRatio}</td><td>${s.buffer.join(' × ')}</td><td>${(s.pixelReductionVsUncapped * 100).toFixed(2)}%</td></tr>`).join('')
  await sheet.setContent(`<style>body{margin:0;padding:24px;background:#062246;color:#edf5ff;font:18px system-ui}h1{margin:0 0 24px}section{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}figure{margin:0}img{width:100%}figcaption{font-size:14px;padding:8px 0}table{margin-top:24px;width:100%;border-collapse:collapse}td,th{text-align:left;padding:8px;border-bottom:1px solid #426384}p{font-size:14px}</style><h1>Step 16 · Shared DPR limit</h1><section>${cards.join('')}</section><table><tr><th>Device DPR</th><th>Renderer DPR</th><th>Buffer (both entries)</th><th>Fewer pixels vs uncapped</th></tr>${rows}</table><p>Chrome ${browser.version()} · 1440 × 900 CSS viewport · CDP emulation · antialias enabled · Pixel savings are not GPU timing measurements.</p>`)
  await sheet.screenshot({ path: file('resolution-contact-sheet.png'), fullPage: true })
  console.log(JSON.stringify(samples.map(({ entry, dpr, buffer, effectiveRatio }) => ({ entry, dpr, buffer, effectiveRatio })), null, 2))
} finally {
  await browser.close()
}
