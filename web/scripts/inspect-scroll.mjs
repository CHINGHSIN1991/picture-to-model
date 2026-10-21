import { chromium } from '@playwright/test'
import { mkdir, readFile, writeFile } from 'node:fs/promises'

const baseUrl = process.env.VIEWER_URL ?? 'http://127.0.0.1:5173'
const output = new URL('../screenshots/', import.meta.url)
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome' })
const errors = []
const file = (name) => new URL(name, output).pathname
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 })
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()) })
  await page.goto(`${baseUrl}/?inspect`)
  await page.locator('.site[data-state="ready"]').waitFor()
  await page.waitForTimeout(400)
  const steps = await page.locator('.story-step').evaluateAll((nodes) => nodes.map((node) => {
    const bounds = node.getBoundingClientRect()
    return { id: node.firstElementChild.id, top: bounds.top + scrollY, end: bounds.bottom + scrollY - innerHeight }
  }))
  const evidence = []
  for (const step of steps) {
    const points = ['hero', 'cta'].includes(step.id) ? [['end', step.end]]
      : [['entry', step.top], ['middle', (step.top + step.end) / 2], ['end', step.end - 1]]
    for (const [phase, top] of points) {
      await page.evaluate((top) => window.scrollTo({ top, behavior: 'instant' }), top)
      await page.waitForTimeout(2500)
      const filename = `scroll-${step.id}-${phase}.png`
      await page.screenshot({ path: file(filename) })
      const state = await page.evaluate(() => window.__reefScene)
      evidence.push({ section: step.id, phase, screenshot: filename, ...state })
    }
  }
  const model = await page.evaluate(async () => {
    const { inspectParts } = await import('/tests/fixtures/inspectParts.ts')
    const result = await inspectParts()
    return { before: result.before, after: result.after, instances: result.report, matrixError: result.matrixError,
      pixelMeanAbsoluteError: result.pixelMeanAbsoluteError, comparison: result.comparison, samePixels: result.samePixels, restoredPixels: result.restoredPixels }
  })
  for (const phase of ['before', 'after']) await writeFile(file(`instances-${phase}.png`), Buffer.from(model.comparison[phase].split(',')[1], 'base64'))
  delete model.comparison
  const performance = await page.evaluate(async () => {
    const canvas = document.querySelector('canvas')
    const gl = canvas.getContext('webgl2')
    const extension = gl.getExtension('WEBGL_debug_renderer_info')
    const renderer = extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)
    const max = document.documentElement.scrollHeight - innerHeight
    const intervals = await new Promise((resolve) => {
      const values = []
      let start, previous
      function frame(time) {
        start ??= time
        if (previous !== undefined) values.push(time - previous)
        previous = time
        window.scrollTo({ top: max * (0.5 - 0.5 * Math.cos((time - start) / 5000 * Math.PI * 2)), behavior: 'instant' })
        if (time - start < 5000) requestAnimationFrame(frame)
        else resolve(values)
      }
      requestAnimationFrame(frame)
    })
    const sorted = [...intervals].sort((a, b) => a - b)
    return { renderer, viewport: [innerWidth, innerHeight], dpr: devicePixelRatio, frames: intervals.length,
      averageFps: 1000 * intervals.length / intervals.reduce((a, b) => a + b, 0), p95FrameMs: sorted[Math.floor(sorted.length * 0.95)] }
  })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.locator('.nav a[href="#model"]').click()
  await page.waitForTimeout(250)
  const reduced = await page.evaluate(() => ({ state: window.__reefScene.state, holds: document.querySelectorAll('.story-hold').length }))
  await page.setViewportSize({ width: 390, height: 844 })
  await page.waitForTimeout(300)
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }))
  await page.waitForTimeout(300)
  await page.screenshot({ path: file('scroll-mobile.png') })
  const mobile = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, viewport: innerWidth }))
  const sheet = await browser.newPage({ viewport: { width: 1440, height: 1440 }, deviceScaleFactor: 1 })
  const cards = await Promise.all(evidence.filter((item) => item.phase === 'end').map(async (item) => {
    const data = (await readFile(file(item.screenshot))).toString('base64')
    return `<figure><img src="data:image/png;base64,${data}"><figcaption>${item.section} · Y ${item.state.rotation[1].toFixed(0)}°</figcaption></figure>`
  }))
  await sheet.setContent(`<style>body{margin:0;background:#05204d;color:white;font:16px system-ui;display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:12px}figure{margin:0}img{width:100%;display:block}figcaption{padding:8px}</style>${cards.join('')}`)
  await sheet.locator('img').evaluateAll((images) => Promise.all(images.map((img) => img.decode())))
  await sheet.screenshot({ path: file('scroll-contact-sheet.png'), fullPage: true })
  const report = { measuredAt: new Date().toISOString(), baseUrl, browser: browser.version(),
    method: '5-second RAF sample during full forward/reverse scroll with parts, shadows and water enabled; default GPU',
    performance, model, reduced, mobile, errors, evidence }
  await writeFile(file('scroll-report.json'), `${JSON.stringify(report, null, 2)}\n`)
  console.log(JSON.stringify({ ...report, evidence: evidence.map(({ section, phase, state }) => ({ section, phase, state })) }, null, 2))
  if (errors.length) process.exitCode = 1
} finally {
  await browser.close()
}
