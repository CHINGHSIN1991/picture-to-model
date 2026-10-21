// Step 15: real scrolling and real tab switching in headed Chrome, plus a DevTools trace.
import { chromium } from '@playwright/test'
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { spawn } from 'node:child_process'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { gzipSync } from 'node:zlib'
import assert from 'node:assert/strict'

const baseUrl = process.env.VIEWER_URL ?? 'http://127.0.0.1:5173'
const output = new URL('../screenshots/', import.meta.url)
const file = (name) => new URL(name, output).pathname
await mkdir(output, { recursive: true })
// Use a temporary standalone Chrome profile: normal Playwright launch forces focus,
// so bringToFront alone cannot reproduce document.visibilityState === 'hidden'.
const profile = await mkdtemp(join(tmpdir(), 'reef-visibility-'))
const chrome = spawn(process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', [
  `--user-data-dir=${profile}`, '--remote-debugging-port=0', '--no-first-run', '--no-default-browser-check',
  '--window-size=1440,1000', 'about:blank',
], { stdio: ['ignore', 'ignore', 'pipe'] })
const endpoint = await new Promise((resolve, reject) => {
  let stderr = ''
  chrome.stderr.on('data', (data) => {
    stderr += data.toString()
    const match = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/)
    if (match) resolve(match[1])
  })
  chrome.once('error', reject)
  chrome.once('exit', (code) => reject(new Error(`Chrome exited: ${code}`)))
})
const browser = await chromium.connectOverCDP(endpoint, { noDefaults: true })
const context = browser.contexts()[0]
const page = await context.newPage()
await page.setViewportSize({ width: 1440, height: 900 })
const errors = []
page.on('pageerror', (error) => errors.push(error.message))
const cdp = await context.newCDPSession(page)
const traceEvents = []
cdp.on('Tracing.dataCollected', ({ value }) => traceEvents.push(...value))
const snapshot = () => page.evaluate(() => window.__reefScene.rendering)
const scroll = (top) => page.evaluate((y) => window.scrollTo({ top: y, behavior: 'instant' }), top)
const waitPaused = (paused) => page.waitForFunction((expected) => window.__reefScene.rendering.paused === expected, paused, { polling: 100 })
const phases = []
async function sample(name, paused, screenshot) {
  await waitPaused(paused)
  await page.waitForTimeout(150)
  await page.evaluate((name) => performance.mark(`${name}:start`), name)
  const before = await snapshot()
  await page.waitForTimeout(1000)
  const after = await snapshot()
  await page.evaluate((name) => performance.mark(`${name}:end`), name)
  const state = await page.evaluate(() => document.visibilityState)
  const result = { name, visibilityState: state, paused, before, after, renderedFrames: after.frames - before.frames, waterAdvance: after.waterTime - before.waterTime }
  if (paused) { assert.equal(result.renderedFrames, 0); assert.equal(result.waterAdvance, 0) }
  else assert.ok(result.renderedFrames > 0)
  if (screenshot) await page.screenshot({ path: file(screenshot) })
  phases.push(result)
  console.log(`${name}: ${result.renderedFrames} frames; document ${state}`)
}

try {
  await page.goto(`${baseUrl}/?mode=live&inspect`)
  await page.bringToFront()
  await page.locator('.site[data-state="ready"]').waitFor()
  await page.waitForTimeout(1000)
  await cdp.send('Tracing.start', { categories: 'devtools.timeline,disabled-by-default-devtools.timeline.stack,blink.user_timing', transferMode: 'ReportEvents' })
  await sample('visible', false, 'visibility-live.png')
  // The existing CTA includes 3D. This fixture adds a genuinely content-only region.
  await page.evaluate(() => {
    const aside = document.createElement('aside')
    aside.id = 'visibility-fixture'
    aside.style.cssText = 'height:200vh;position:relative;background:#062246;color:#edf5ff;padding:10vh 8vw;box-sizing:border-box;font:24px system-ui'
    aside.innerHTML = '<h1>Content-only region</h1><p>Visibility test fixture · outside Hero–CTA</p><p>The 3D scene is paused.</p>'
    document.body.append(aside)
    window.scrollTo({ top: aside.offsetTop, behavior: 'instant' })
  })
  await sample('offscreen', true, 'visibility-offscreen.png')
  await scroll(0)
  await sample('returned', false)
  const other = await context.newPage()
  await other.setContent('<title>Tab visibility check</title><h1>Another tab</h1>')
  await other.bringToFront()
  await page.waitForFunction(() => document.visibilityState === 'hidden', undefined, { polling: 100 })
  await sample('hidden-tab', true)
  await page.bringToFront()
  await sample('resumed', false, 'visibility-resumed.png')
  await other.close()
  const complete = new Promise((resolve) => cdp.once('Tracing.tracingComplete', resolve))
  await cdp.send('Tracing.end')
  await complete
  for (const phase of phases) {
    const start = traceEvents.find((event) => event.name === `${phase.name}:start`)?.ts
    const end = traceEvents.find((event) => event.name === `${phase.name}:end`)?.ts
    assert.ok(start && end, `missing trace markers: ${phase.name}`)
    const functions = traceEvents.filter((event) => event.name === 'FunctionCall' && event.ts >= start && event.ts <= end)
    phase.threeAnimationCallbacks = functions.filter((event) => event.args?.data?.functionName === 'onAnimationFrame' && /three|chunk-/i.test(event.args?.data?.url ?? event.args?.data?.scriptName ?? '')).length
    phase.animationCallbacks = functions.filter((event) => event.args?.data?.functionName === 'onAnimationFrame').map((event) => event.args.data).slice(0, 1)
    if (phase.paused) assert.equal(phase.threeAnimationCallbacks, 0)
    else assert.ok(phase.threeAnimationCallbacks > 0, `missing Three.js callbacks: ${phase.name}`)
  }
  await writeFile(file('visibility-trace.json.gz'), gzipSync(JSON.stringify({ traceEvents })))
  const report = { measuredAt: new Date().toISOString(), browser: browser.version(), baseUrl,
    method: 'Headed Chrome; real IntersectionObserver scrolling into an injected opaque content-only region; real background tab via bringToFront; 1-second samples; DevTools trace FunctionCall onAnimationFrame in Three.js. Other page rAF callbacks may continue.',
    phases, errors }
  await writeFile(file('visibility-report.json'), `${JSON.stringify(report, null, 2)}\n`)
  assert.deepEqual(errors, [])
  const sheet = await context.newPage()
  await sheet.setViewportSize({ width: 1440, height: 650 })
  const cards = await Promise.all([
    ['visibility-live.png', 'Visible · rendering'], ['visibility-offscreen.png', 'Offscreen fixture · paused'], ['visibility-resumed.png', 'Returned from background tab · rendering'],
  ].map(async ([name, caption]) => `<figure><img src="data:image/png;base64,${(await readFile(file(name))).toString('base64')}"><figcaption>${caption}</figcaption></figure>`))
  const rows = phases.map((phase) => `<tr><td>${phase.name}</td><td>${phase.visibilityState}</td><td>${phase.renderedFrames}</td><td>${phase.threeAnimationCallbacks}</td><td>${phase.waterAdvance.toFixed(3)}</td></tr>`).join('')
  await sheet.setContent(`<style>body{margin:0;padding:24px;background:#062246;color:#edf5ff;font:18px system-ui}h1{margin:0 0 24px}section{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}figure{margin:0}img{width:100%}figcaption{font-size:15px;padding:8px 0}table{margin-top:24px;width:100%;border-collapse:collapse}td,th{text-align:left;padding:8px;border-bottom:1px solid #426384}p{font-size:14px}</style><h1>Step 15 · Scene visibility</h1><section>${cards.join('')}</section><table><tr><th>Phase (1 second)</th><th>Document</th><th>Rendered frames</th><th>Three rAF callbacks</th><th>Water time Δ</th></tr>${rows}</table><p>Real scroll + real background tab · Chrome ${browser.version()} · Injected content-only fixture; existing Hero–CTA all contain 3D.</p>`)
  await sheet.screenshot({ path: file('visibility-contact-sheet.png'), fullPage: true })
} finally {
  await browser.close()
  const exited = new Promise((resolve) => chrome.once('exit', resolve))
  chrome.kill('SIGTERM')
  await exited
  await rm(profile, { recursive: true, force: true })
}
