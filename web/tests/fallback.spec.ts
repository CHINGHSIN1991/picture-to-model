import { expect, test } from '@playwright/test'
import { decideRenderMode, type RenderSignals } from '../src/composables/useRenderMode'

const threeD = /\/Scene[.-]|ScrollController|\/deps\/three|\/deps\/gsap|gsap\/|\/framing-|\.glb/
const desktop: RenderSignals = {
  reducedMotion: false, saveData: false, webgl: true, maxTextureSize: 16384, cores: 8, memory: 8, dpr: 2,
  width: 1440, height: 900, coarsePointer: false, finePointer: true, touchPoints: 0,
}
const phone: RenderSignals = { ...desktop, width: 390, height: 844, dpr: 3, coarsePointer: true, finePointer: false, touchPoints: 5, cores: 6, memory: 4 }

test('decides from several signals, never from width alone', () => {
  expect(decideRenderMode(desktop)).toEqual({ mode: 'live', reason: 'capable' })
  expect(decideRenderMode(phone).mode).toBe('static')
  expect(decideRenderMode({ ...phone, width: 844, height: 390 }).reason).toBe('touch-small-screen')
  // A narrow desktop window keeps a fine pointer, so it stays live.
  expect(decideRenderMode({ ...desktop, width: 600 }).mode).toBe('live')
  // iPad: desktop-like UA, several touch points, short side ≥ 768 and enough hardware.
  expect(decideRenderMode({ ...phone, width: 834, height: 1194 }).mode).toBe('live')
  expect(decideRenderMode({ ...phone, width: 744, height: 1133 }).mode).toBe('static')
  // iPad with a trackpad is still an iPad.
  expect(decideRenderMode({ ...phone, finePointer: true, touchPoints: 5, width: 744, height: 1133 }).mode).toBe('static')
  expect(decideRenderMode({ ...desktop, reducedMotion: true }).reason).toBe('reduced-motion')
  expect(decideRenderMode({ ...desktop, saveData: true }).reason).toBe('save-data')
  expect(decideRenderMode({ ...desktop, webgl: false, maxTextureSize: 0 }).reason).toBe('no-webgl')
  expect(decideRenderMode({ ...desktop, maxTextureSize: 1024 }).reason).toBe('small-texture')
  expect(decideRenderMode({ ...desktop, cores: 2 }).reason).toBe('low-end')
  expect(decideRenderMode({ ...desktop, memory: 2 }).reason).toBe('low-end')
  expect(decideRenderMode({ ...desktop, width: 1920, dpr: 2, cores: 4 }).reason).toBe('high-dpr-few-cores')
  expect(decideRenderMode({ ...desktop, width: 1920, dpr: 2, cores: 8 }).mode).toBe('live')
  expect(decideRenderMode({ ...desktop, reducedMotion: true }, 'live')).toEqual({ mode: 'live', reason: 'query' })
  expect(decideRenderMode(desktop, 'static').mode).toBe('static')
  expect(decideRenderMode(desktop, 'other').mode).toBe('live')
})

test('serves a phone the WebP still and never requests Three.js, GSAP or the GLB', async ({ browser }) => {
  const context = await browser.newContext({ hasTouch: true, isMobile: true, viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 })
  const page = await context.newPage()
  const requests: string[] = []
  const errors: string[] = []
  page.on('request', (request) => requests.push(request.url()))
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()) })
  await page.goto('/')
  const site = page.locator('.site')
  await expect(site).toHaveAttribute('data-state', 'ready')
  await expect(site).toHaveAttribute('data-mode', 'static')
  await expect(site).toHaveAttribute('data-mode-reason', 'touch-small-screen')
  await expect(page.locator('canvas')).toHaveCount(0)
  const still = page.locator('.stage picture.still img')
  await expect(still).toBeVisible()
  // naturalWidth is divided by the srcset density, so the chosen candidate is checked by URL.
  await expect.poll(() => still.evaluate((image: HTMLImageElement) => image.complete && image.naturalWidth > 0 && new URL(image.currentSrc).pathname)).toBe('/fallback/hero-portrait@2x.webp')
  expect(await page.locator('.stage').boundingBox()).toMatchObject({ x: 0, y: 0, width: 390, height: 844 })
  expect(await still.boundingBox()).toMatchObject({ x: 0, y: 0, width: 390, height: 844 })
  // Copy and navigation still work without the controller.
  await page.locator('#hero a[href="#upload"]').tap()
  await expect.poll(async () => (await page.locator('#upload').boundingBox())!.y).toBeLessThan(2)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
  await page.waitForTimeout(300)
  expect(requests.filter((url) => threeD.test(url))).toEqual([])
  expect(requests.some((url) => url.endsWith('/fallback/hero-portrait@2x.webp'))).toBe(true)
  expect(errors).toEqual([])
  await context.close()
})

test('keeps the live scene on desktops, honours reduced motion, and lets ?mode= override', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()
  const requests: string[] = []
  page.on('request', (request) => requests.push(request.url()))
  await page.goto('/')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'ready')
  await expect(page.locator('.site')).toHaveAttribute('data-mode', 'live')
  await expect(page.locator('canvas')).toHaveCount(1)
  expect(requests.some((url) => url.endsWith('/models/reef.glb'))).toBe(true)
  // A narrow desktop window is not a phone.
  await page.setViewportSize({ width: 600, height: 900 })
  await page.goto('/')
  await expect(page.locator('.site')).toHaveAttribute('data-mode', 'live')
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  requests.length = 0
  await page.goto('/')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'ready')
  await expect(page.locator('.site')).toHaveAttribute('data-mode-reason', 'reduced-motion')
  await expect(page.locator('canvas')).toHaveCount(0)
  const still = page.locator('.stage img')
  await expect.poll(() => still.evaluate((image: HTMLImageElement) => image.complete && new URL(image.currentSrc).pathname)).toBe('/fallback/hero-landscape.webp')
  expect(requests.filter((url) => threeD.test(url))).toEqual([])
  await page.goto('/?mode=live')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'ready')
  await expect(page.locator('.site')).toHaveAttribute('data-mode-reason', 'query')
  await expect(page.locator('canvas')).toHaveCount(1)
  await context.close()
  // A phone can be forced live for asset capture.
  const touch = await browser.newContext({ hasTouch: true, isMobile: true, viewport: { width: 390, height: 844 } })
  const forced = await touch.newPage()
  await forced.goto('/?mode=static')
  await expect(forced.locator('.site')).toHaveAttribute('data-mode-reason', 'query')
  await forced.goto('/?mode=live')
  await expect(forced.locator('.site')).toHaveAttribute('data-state', 'ready')
  await expect(forced.locator('canvas')).toHaveCount(1)
  await touch.close()
})
