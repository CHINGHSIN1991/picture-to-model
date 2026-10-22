import { expect, test, type Page } from '@playwright/test'
import { sections } from '../src/three/config/sections'
import type { SceneSnapshot } from '../src/three/Scene'

const snapshot = (page: Page): Promise<SceneSnapshot> => page.evaluate(() => (window as any).__reefScene)
const scroll = (page: Page, y: number) => page.evaluate((top) => window.scrollTo({ top, behavior: 'instant' }), y)
const geometry = (page: Page) => page.locator('.story-step').evaluateAll((nodes) => nodes.map((node) => {
  const bounds = node.getBoundingClientRect()
  return { top: bounds.top + scrollY, height: bounds.height, end: bounds.bottom + scrollY - innerHeight }
}))

test('scrubs every section, holds copy for parts, reverses exactly and adds pointer offsets', async ({ page }, testInfo) => {
  test.setTimeout(60000)
  await page.setViewportSize({ width: 1440, height: 900 })
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/?inspect')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'ready')
  await page.waitForTimeout(200)
  const rest = await snapshot(page)
  const positions = await geometry(page)
  expect(await page.locator('.story-hold').count()).toBe(4)
  // Halfway between Hero and upload is a true interpolated state.
  await scroll(page, positions[1]!.top - 450)
  await expect.poll(async () => (await snapshot(page)).state.rotation[1]).toBeCloseTo(-17.5, 1)
  for (let i = 1; i < sections.length; i++) {
    const target = sections[i]!
    if (target.partsOnEnter) {
      await scroll(page, positions[i]!.top + 100)
      await expect.poll(async () => Math.abs((await snapshot(page)).state.rotation[1] - target.rotation[1])).toBeLessThan(0.01)
      expect((await page.locator(`#${target.id}`).boundingBox())!.y).toBeCloseTo(0, 0)
      const parts = (await snapshot(page)).state.parts
      for (const key of Object.keys(target.partsOnEnter) as (keyof typeof parts)[]) {
        expect(parts[key]).toBeGreaterThan(0.5)
      }
    }
    await scroll(page, positions[i]!.end - 1)
    await expect.poll(async () => Math.abs((await snapshot(page)).state.rotation[1] - target.rotation[1])).toBeLessThan(0.2)
    await expect.poll(async () => {
      const parts = (await snapshot(page)).state.parts
      return Math.max(...(Object.keys(target.parts) as (keyof typeof parts)[]).map((key) => Math.abs(parts[key] - target.parts[key])))
    }).toBeLessThan(0.005)
    const current = (await snapshot(page)).state
    expect(current.position[0]).toBeCloseTo(target.position[0], 2)
    expect(current.camera.elevation).toBeCloseTo(target.camera.elevation, 1)
    expect(current.emissive).toBeCloseTo(target.emissive, 2)
    for (const key of Object.keys(target.parts) as (keyof typeof target.parts)[]) expect(current.parts[key]).toBeCloseTo(target.parts[key], 2)
  }
  await page.screenshot({ path: testInfo.outputPath('scroll-cta.png') })
  // Scrub backwards to the exact same endpoint, including original local transforms.
  await scroll(page, 0)
  await expect.poll(async () => (await snapshot(page)).state.rotation[1]).toBe(0)
  await expect.poll(async () => (await snapshot(page)).parts, { timeout: 10000 }).toEqual(rest.parts)
  await scroll(page, positions[2]!.top + 450)
  await page.mouse.move(1439, 899)
  await page.waitForTimeout(700)
  const tilted = await snapshot(page)
  expect(tilted.rotation[1]! - tilted.state.rotation[1] * Math.PI / 180).toBeGreaterThan(0.1)
  expect(tilted.rotation[1]! - tilted.state.rotation[1] * Math.PI / 180).toBeLessThanOrEqual(0.15)
  expect(errors).toEqual([])
})

test('supports deep links, resize, reduced motion changes, and scoped cleanup', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/?inspect#controls')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'ready')
  await expect.poll(async () => (await snapshot(page)).state.rotation[1]).toBeCloseTo(-160, 1)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await expect(page.locator('.story-hold')).toHaveCount(0)
  await page.locator('.nav a', { hasText: '行程' }).click()
  await expect.poll(async () => (await snapshot(page)).state).toEqual(sections[2])
  const parts = (await snapshot(page)).parts
  await page.waitForTimeout(200)
  expect((await snapshot(page)).parts).toEqual(parts)
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await expect(page.locator('.story-hold')).toHaveCount(4)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.waitForTimeout(250)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
  await scroll(page, 100000)
  await expect.poll(async () => (await snapshot(page)).state.rotation[1]).toBe(-360)
  // Mount and dispose another controller without killing the app's six triggers.
  const cleanup = await page.evaluate(async () => {
    const path = '/src/three/ScrollController.ts'
    const { ScrollController } = await import(/* @vite-ignore */ path)
    // Inspect via DOM ownership rather than relying on an internal GSAP module identity.
    const host = document.createElement('main')
    const statePath = '/src/three/config/sections.ts'
    const { sections } = await import(/* @vite-ignore */ statePath)
    host.innerHTML = sections.map((s: any) => `<div class="story-step"><section id="test-${s.id}" style="height:100px"></section></div>`).join('')
    document.body.append(host)
    const controller = new ScrollController(host, sections.map((s: any) => ({ ...s, id: `test-${s.id}` })))
    controller.dispose()
    controller.dispose()
    const styles = [...host.children].map((node) => node.getAttribute('style') || null)
    host.remove()
    return { styles }
  })
  expect(cleanup.styles).toEqual([null, null, null, null, null, null])
  await scroll(page, 0)
  await expect.poll(async () => (await snapshot(page)).state.rotation[1]).toBe(0)
  expect(errors).toEqual([])
})

test('instances preserve rest geometry, reduce draw calls, and all part modes restore exactly', async ({ page }) => {
  await page.goto('/?state=1')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'ready')
  const result = await page.evaluate(async () => {
    const path = '/tests/fixtures/inspectParts.ts'
    const { inspectParts } = await import(/* @vite-ignore */ path)
    return inspectParts()
  })
  expect(result.after.calls).toBeLessThan(result.before.calls * 0.65)
  expect(result.after.triangles).toBe(result.before.triangles)
  expect(result.matrixError).toBeLessThan(1e-6)
  expect(result.pixelMeanAbsoluteError).toBeLessThan(1)
  expect(result.restored).toEqual(result.rest)
  expect(result.restoredPixels).toBe(true)
  expect(result.hidden).toMatchObject({ rocks: true, corals: true, kelp: true, fish: true, diver: true, boulders: false })
  expect(result.intermediate).not.toEqual(result.rest)
  expect(result.intermediate).not.toEqual(result.departed)
  expect(new Set(result.coralScales).size).toBeGreaterThan(1)
  expect(result.stagger.hidden).toBeGreaterThan(0)
  expect(result.stagger.hidden).toBeLessThan(result.stagger.total)
  expect(result.swapped.Coral_BranchA_001).not.toEqual(result.rest.Coral_BranchA_001)
})
