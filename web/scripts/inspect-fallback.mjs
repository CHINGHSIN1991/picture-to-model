// Step 14 evidence: which mode each device gets, what the static page downloads, and how close
// the still is to the live hero frame on the same phone viewport.
// Run against `bun run build && bun run preview` (VIEWER_URL=http://127.0.0.1:4173) for production byte counts; the dev server also works.
import { chromium, devices } from '@playwright/test'
import { mkdir, readFile, writeFile } from 'node:fs/promises'

const baseUrl = process.env.VIEWER_URL ?? 'http://127.0.0.1:5173'
const output = new URL('../screenshots/', import.meta.url)
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome' })
const file = (name) => new URL(name, output).pathname
const threeD = /\/Scene[.-]|ScrollController|\/deps\/three|\/deps\/gsap|gsap\/|\/framing-|\.glb/
const errors = []
const phone = { hasTouch: true, isMobile: true, viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 }

async function visit(name, contextOptions, url, { reducedMotion, screenshot, scrollToEnd } = {}) {
  const context = await browser.newContext(contextOptions)
  const page = await context.newPage()
  const requests = []
  page.on('request', (request) => requests.push(request.url()))
  page.on('pageerror', (error) => errors.push(`${name}: ${error.message}`))
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`${name}: ${message.text()}`) })
  if (reducedMotion) await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto(`${baseUrl}${url}`)
  await page.locator('.site[data-state="ready"]').waitFor()
  await page.evaluate(() => Promise.all([...document.images].map((image) => image.decode().catch(() => undefined))))
  await page.waitForTimeout(600)
  const result = await page.evaluate(() => {
    const site = document.querySelector('.site')
    const image = document.querySelector('.stage img')
    const resources = performance.getEntriesByType('resource')
    return {
      mode: site.dataset.mode, reason: site.dataset.modeReason,
      viewport: [innerWidth, innerHeight], dpr: devicePixelRatio, scrollWidth: document.documentElement.scrollWidth,
      canvases: document.querySelectorAll('canvas').length,
      still: image ? { currentSrc: new URL(image.currentSrc).pathname, natural: [image.naturalWidth, image.naturalHeight] } : null,
      resourceCount: resources.length,
      transferredKB: Math.round(resources.reduce((sum, entry) => sum + (entry.transferSize || entry.encodedBodySize || 0), 0) / 1024),
    }
  })
  result.name = name
  result.requests = requests.length
  result.threeDRequests = requests.filter((request) => threeD.test(request)).map((request) => new URL(request).pathname)
  if (screenshot) {
    result.screenshot = screenshot
    await page.screenshot({ path: file(screenshot) })
  }
  if (scrollToEnd) {
    await page.evaluate(() => window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'instant' }))
    await page.waitForTimeout(400)
    result.endScreenshot = scrollToEnd
    await page.screenshot({ path: file(scrollToEnd) })
    result.endSection = await page.evaluate(() => [...document.querySelectorAll('main section')].findLast((section) => section.getBoundingClientRect().top < innerHeight * 0.5)?.id)
  }
  await context.close()
  return result
}

async function compare(a, b) {
  const page = await browser.newPage()
  const result = await page.evaluate(async ([a, b]) => {
    const load = async (data) => { const image = new Image(); image.src = `data:image/png;base64,${data}`; await image.decode(); return image }
    const [x, y] = await Promise.all([load(a), load(b)])
    const canvas = document.createElement('canvas')
    canvas.width = x.naturalWidth; canvas.height = x.naturalHeight
    const context = canvas.getContext('2d', { willReadFrequently: true })
    const read = (image) => { context.drawImage(image, 0, 0); return context.getImageData(0, 0, canvas.width, canvas.height).data }
    const p = read(x), q = read(y)
    let sum = 0, over = 0
    for (let i = 0; i < p.length; i += 4) {
      const d = (Math.abs(p[i] - q[i]) + Math.abs(p[i + 1] - q[i + 1]) + Math.abs(p[i + 2] - q[i + 2])) / 3
      sum += d
      if (d > 24) over++
    }
    return { size: [canvas.width, canvas.height], meanAbsoluteError: sum / (p.length / 4), pixelsOver24: over / (p.length / 4) }
  }, [(await readFile(file(a))).toString('base64'), (await readFile(file(b))).toString('base64')])
  await page.close()
  return result
}

try {
  const scenarios = [
    await visit('phone-static', phone, '/', { screenshot: 'fallback-mobile.png', scrollToEnd: 'fallback-mobile-cta.png' }),
    await visit('phone-live', phone, '/?mode=live', { screenshot: 'fallback-mobile-live.png' }),
    await visit('phone-landscape', { ...phone, viewport: { width: 844, height: 390 } }, '/', { screenshot: 'fallback-mobile-landscape.png' }),
    await visit('desktop-reduced-motion', { viewport: { width: 1440, height: 900 } }, '/', { reducedMotion: true, screenshot: 'fallback-desktop-reduced.png' }),
    await visit('desktop', { viewport: { width: 1440, height: 900 } }, '/'),
    await visit('desktop-narrow-window', { viewport: { width: 600, height: 900 } }, '/'),
    await visit('ipad-pro-11', { ...devices['iPad Pro 11'], viewport: devices['iPad Pro 11'].viewport }, '/'),
  ]
  const match = await compare('fallback-mobile.png', 'fallback-mobile-live.png')
  const manifest = JSON.parse(await readFile(new URL('../public/fallback/manifest.json', import.meta.url), 'utf8'))
  const sheet = await browser.newPage({ viewport: { width: 1440, height: 400 }, deviceScaleFactor: 1 })
  const panels = [
    ['fallback-mobile-live.png', '手機 · ?mode=live（WebGL）'],
    ['fallback-mobile.png', '手機 · static（WebP，無 three / GLB）'],
    ['fallback-desktop-reduced.png', '桌機 · reduced-motion → static'],
  ]
  const cards = await Promise.all(panels.map(async ([name, caption]) => {
    const data = (await readFile(file(name))).toString('base64')
    return `<figure><img src="data:image/png;base64,${data}"><figcaption>${caption}</figcaption></figure>`
  }))
  await sheet.setContent(`<style>body{margin:0;background:#05204d;color:white;font:16px system-ui;display:grid;grid-template-columns:1fr 1fr 2.2fr;gap:12px;padding:12px;align-items:start}figure{margin:0}img{width:100%;display:block}figcaption{padding:8px}</style>${cards.join('')}`)
  await sheet.screenshot({ path: file('fallback-contact-sheet.png'), fullPage: true })
  await sheet.close()
  const report = {
    measuredAt: new Date().toISOString(), baseUrl, browser: browser.version(),
    method: 'Chrome device emulation (touch + mobile viewport); 3D requests matched by Scene/ScrollController/three/gsap/framing chunk/.glb; transferredKB from PerformanceResourceTiming; still vs live compared per RGB pixel on the same 390×844 @2x viewport',
    stills: manifest, scenarios, stillVsLive: match, errors,
  }
  await writeFile(file('fallback-report.json'), `${JSON.stringify(report, null, 2)}\n`)
  for (const item of scenarios) console.log(`${item.name.padEnd(24)} ${item.mode.padEnd(7)} ${item.reason.padEnd(20)} 3D requests: ${item.threeDRequests.length} / ${item.requests} total, ${item.transferredKB} KB, still: ${item.still?.currentSrc ?? '-'}`)
  console.log('still vs live:', JSON.stringify(match))
  if (errors.length) { console.error(errors); process.exitCode = 1 }
} finally {
  await browser.close()
}
