import { expect, test } from '@playwright/test'
import { createHash } from 'node:crypto'

const checksum = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex')

test('damps bounded offsets consistently across frame rates, resets on exit, and releases listeners', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'ready')
  const result = await page.evaluate(async () => {
    const path = '/src/three/InteractionController.ts'
    const { InteractionController } = await import(/* @vite-ignore */ path)
    const configPath = '/src/three/config/pointer.ts'
    const { pointerConfig } = await import(/* @vite-ignore */ configPath)
    const simulate = (fps: number) => {
      const controller = new InteractionController()
      controller.setPointer(5, -5)
      const first = { ...controller.update(1 / fps) }
      for (let i = 1; i < fps; i++) controller.update(1 / fps)
      const settled = { ...controller.update(0) }
      controller.dispose()
      return { first, settled }
    }
    const rates = [30, 60, 120].map(simulate)
    const controller = new InteractionController()
    window.dispatchEvent(new PointerEvent('pointermove', { pointerType: 'mouse', clientX: innerWidth, clientY: innerHeight }))
    const moved = { ...controller.update(1) }
    // Moving between DOM elements must not reset the target.
    window.dispatchEvent(new PointerEvent('pointerout', { relatedTarget: document.body }))
    const internal = { ...controller.update(1) }
    window.dispatchEvent(new PointerEvent('pointerout', { relatedTarget: null }))
    const returning = { ...controller.update(1 / 60) }
    const neutral = { ...controller.update(3) }
    window.dispatchEvent(new PointerEvent('pointermove', { pointerType: 'touch', clientX: innerWidth, clientY: innerHeight }))
    const touch = { ...controller.update(1) }
    const exits = ['pointerleave', 'pointercancel', 'blur'].map((event) => {
      controller.setPointer(1, 1)
      controller.update(1)
      window.dispatchEvent(new Event(event))
      return { ...controller.update(3) }
    })
    controller.dispose()
    controller.dispose()
    window.dispatchEvent(new PointerEvent('pointermove', { pointerType: 'mouse', clientX: innerWidth, clientY: innerHeight }))
    const disposed = { ...controller.update(1) }
    const disabled = new InteractionController({ ...pointerConfig, mode: 'none' })
    disabled.setPointer(1, 1)
    const none = { ...disabled.update(1) }
    disabled.dispose()
    return { rates, moved, internal, returning, neutral, touch, exits, disposed, none }
  })
  for (const { first, settled } of result.rates) {
    expect(first.x).toBeGreaterThan(-0.08)
    expect(first.x).toBeLessThan(0)
    expect(first.y).toBeGreaterThan(0)
    expect(first.y).toBeLessThan(settled.y)
    expect(settled.x).toBeGreaterThanOrEqual(-0.08)
    expect(settled.y).toBeLessThanOrEqual(0.15)
    expect(settled.y).toBeCloseTo(result.rates[0].settled.y, 10)
  }
  expect(result.internal.y).toBeGreaterThan(result.moved.y)
  expect(result.returning.y).toBeGreaterThan(0)
  expect(result.returning.y).toBeLessThan(result.internal.y)
  for (const offset of [result.neutral, result.touch, result.disposed, result.none, ...result.exits]) {
    expect(offset).toEqual({ x: 0, y: 0 })
  }
})

test('renders tilt on top of a nonzero section rotation, returns to neutral, and preserves scrolling', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  // Freeze only water time so pixel changes prove the actual scene responds to the pointer.
  await page.route('**/src/three/lightingConfig.ts', async (route) => {
    const response = await route.fetch()
    await route.fulfill({ response, body: (await response.text()).replace('animated: true', 'animated: false') })
  })
  await page.goto('/?state=3')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'ready')
  await page.waitForTimeout(200)
  const neutral = checksum(await page.locator('canvas').screenshot())
  await page.mouse.move(1439, 899)
  await page.waitForTimeout(800)
  expect(checksum(await page.locator('canvas').screenshot())).not.toBe(neutral)
  await page.screenshot({ path: testInfo.outputPath('pointer-section-3.png') })
  await page.evaluate(() => window.dispatchEvent(new PointerEvent('pointerout', { relatedTarget: null })))
  await expect.poll(async () => checksum(await page.locator('canvas').screenshot()), { timeout: 8000 }).toBe(neutral)
  // A runtime preference change removes an existing tilt, and later moves stay neutral.
  await page.mouse.move(1, 1)
  await page.waitForTimeout(400)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await expect.poll(async () => checksum(await page.locator('canvas').screenshot())).toBe(neutral)
  await page.mouse.move(1439, 899)
  await page.waitForTimeout(200)
  expect(checksum(await page.locator('canvas').screenshot())).toBe(neutral)
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await page.mouse.move(1000, 700)
  await page.mouse.wheel(0, 600)
  await expect.poll(() => page.evaluate(() => scrollY)).toBeGreaterThan(300)
  await page.locator('.nav a', { hasText: '調光' }).click()
  await expect.poll(async () => (await page.locator('#controls').boundingBox())!.y).toBeLessThan(2)
})

test('disables tilt on a touch-only device', async ({ browser }) => {
  const context = await browser.newContext({ hasTouch: true, isMobile: true, viewport: { width: 390, height: 844 } })
  const page = await context.newPage()
  await page.goto('/')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'ready')
  const offset = await page.evaluate(async () => {
    const path = '/src/three/InteractionController.ts'
    const { InteractionController } = await import(/* @vite-ignore */ path)
    const controller = new InteractionController()
    controller.setPointer(1, 1)
    const value = { ...controller.update(1) }
    controller.dispose()
    return value
  })
  expect(offset).toEqual({ x: 0, y: 0 })
  await page.touchscreen.tap(200, 600)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
  await context.close()
})
