import { chromium } from '@playwright/test'
import { readFile, writeFile } from 'node:fs/promises'
import assert from 'node:assert/strict'
const root = new URL('../reports/performance/', import.meta.url)
const devUrl = process.env.DEV_URL ?? 'http://127.0.0.1:5177'
const baseUrl = process.env.VIEWER_URL ?? 'http://127.0.0.1:4180'
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome' })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' })
  await page.goto(`${devUrl}/?mode=static`)
  const resources = await page.evaluate(async () => {
    const { inspectResources } = await import('/tests/fixtures/inspectResources.ts')
    return inspectResources()
  })
  await writeFile(new URL('after/resources.json', root), `${JSON.stringify(resources, null, 2)}\n`)
  let release
  const pending = new Promise((resolve) => { release = resolve })
  await page.route('**/models/reef.glb', async (route) => { await pending; await route.continue() })
  await page.goto(`${baseUrl}/?mode=live`)
  await page.locator('.stage .still img').waitFor()
  await page.locator('.stage .still img').evaluate((image) => image.decode())
  assert.equal(await page.locator('.site').getAttribute('data-state'), 'loading')
  await page.screenshot({ path: new URL('after/progressive-loading.png', root).pathname, scale: 'css' })
  release()
  await page.locator('.site[data-state="ready"]').waitFor()
  await page.locator('.stage .still').waitFor({ state: 'detached' })
  await page.screenshot({ path: new URL('after/progressive-ready.png', root).pathname, scale: 'css' })
  const load = async (url) => (await readFile(url)).toString('base64')
  const before = await load(new URL('before/desktop-hero.png', root)), after = await load(new URL('after/desktop-hero.png', root))
  const difference = await page.evaluate(async ([before, after]) => {
    const load = async (data) => { const image = new Image(); image.src = `data:image/png;base64,${data}`; await image.decode(); return image }
    const [a, b] = await Promise.all([load(before), load(after)])
    const canvas = document.createElement('canvas'); canvas.width = a.width; canvas.height = a.height
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    const read = (image) => { ctx.drawImage(image, 0, 0); return ctx.getImageData(0, 0, canvas.width, canvas.height).data }
    const x = read(a), y = read(b); let sum = 0, changed = 0
    for (let i = 0; i < x.length; i += 4) { const delta = (Math.abs(x[i] - y[i]) + Math.abs(x[i+1] - y[i+1]) + Math.abs(x[i+2] - y[i+2])) / 3; sum += delta; if (delta > 24) changed++ }
    return { meanAbsoluteRgbError: sum / (x.length / 4), fractionPixelsOver24: changed / (x.length / 4), dimensions: [a.width, a.height] }
  }, [before, after])
  assert.ok(difference.meanAbsoluteRgbError < 1, JSON.stringify(difference))
  await writeFile(new URL('after/visual.json', root), `${JSON.stringify({ resources, difference }, null, 2)}\n`)
  const mockup = await load(new URL('../../../mockups/final-homepage.png', root))
  const cards = [
    [mockup, 'Step 09 mockup · original hero crop', true], [before, 'Before Step 17 · production', false], [after, 'After Step 17 · production', false],
  ].map(([data, caption, crop]) => `<figure><div class="frame"><img class="${crop ? 'crop' : ''}" src="data:image/png;base64,${data}"></div><figcaption>${caption}</figcaption></figure>`)
  await page.setViewportSize({ width: 1440, height: 450 })
  await page.setContent(`<style>body{margin:0;padding:24px;background:#062246;color:#edf5ff;font:17px system-ui}h1{margin:0 0 20px}section{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}figure{margin:0}.frame{height:284px;overflow:hidden}img{width:100%;display:block}.crop{object-fit:cover;object-position:top}figcaption{padding:10px 0}p{font-size:14px}</style><h1>Step 17 · Visual audit</h1><section>${cards.join('')}</section><p>Before/after hero mean RGB error: ${difference.meanAbsoluteRgbError.toFixed(4)} / 255. Original mockup uses a Blender render; production uses the established Three.js lighting.</p>`)
  await page.locator('img').evaluateAll((images) => Promise.all(images.map((image) => image.decode())))
  await page.screenshot({ path: new URL('visual-comparison.png', root).pathname, fullPage: true })
  console.log(JSON.stringify({ resources, difference }, null, 2))
} finally { await browser.close() }
