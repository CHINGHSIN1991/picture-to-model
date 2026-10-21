import { expect, test, type Page } from '@playwright/test'
import type { SceneSnapshot } from '../src/three/Scene'

const snapshot = (page: Page): Promise<SceneSnapshot> => page.evaluate(() => (window as any).__reefScene)
// Synthetic document state makes races reproducible even in headless Chrome.
const visibility = (page: Page, value: 'visible' | 'hidden') => page.evaluate((state) => {
  Object.defineProperty(document, 'visibilityState', { configurable: true, value: state })
  document.dispatchEvent(new Event('visibilitychange'))
}, value)
const scroll = (page: Page, top: number) => page.evaluate((y) => window.scrollTo({ top: y, behavior: 'instant' }), top)

async function frozen(page: Page) {
  await expect.poll(async () => (await snapshot(page)).rendering.paused).toBe(true)
  const before = await snapshot(page)
  await page.waitForTimeout(250)
  const after = await snapshot(page)
  expect(after.rendering).toEqual(before.rendering)
  expect(after.parts).toEqual(before.parts)
  expect(after.rotation).toEqual(before.rotation)
  return after
}

test('pauses outside 3D regions and combines tab visibility without stopping other animation', async ({ page }) => {
  await page.goto('/?inspect&mode=live')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'ready')
  const initial = (await snapshot(page)).rendering.frames
  await expect.poll(async () => (await snapshot(page)).rendering.frames).toBeGreaterThan(initial)
  // CTA footer still contains the model and must stay active.
  await scroll(page, 100000)
  await expect.poll(async () => (await snapshot(page)).state.id).toBe('cta')
  expect((await snapshot(page)).rendering.paused).toBe(false)
  // A real content-only region, outside all six observed wrappers.
  await page.evaluate(async () => {
    const spacer = document.createElement('aside')
    spacer.style.cssText = 'height:200vh;position:relative;background:#fff'
    document.body.append(spacer)
    const path = '/node_modules/gsap/index.js'
    const { gsap } = await import(/* @vite-ignore */ path)
    const target = { value: 0 }
    ;(window as any).__independentTween = target
    gsap.to(target, { value: 100, duration: 10, ease: 'none' })
  })
  await scroll(page, 100000)
  await frozen(page)
  const tweenBefore = await page.evaluate(() => (window as any).__independentTween.value)
  await page.waitForTimeout(150)
  expect(await page.evaluate(() => (window as any).__independentTween.value)).toBeGreaterThan(tweenBefore)
  await visibility(page, 'hidden')
  await scroll(page, 0) // IntersectionObserver must not resume a hidden tab.
  await frozen(page)
  await visibility(page, 'visible')
  await expect.poll(async () => (await snapshot(page)).rendering.paused).toBe(false)
  await expect.poll(async () => (await snapshot(page)).state.id).toBe('hero')
  await visibility(page, 'hidden')
  await frozen(page)
  await scroll(page, 100000)
  await page.waitForTimeout(100)
  await visibility(page, 'visible') // Visible tab must not resume an offscreen scene.
  await frozen(page)
  await scroll(page, 0)
  await expect.poll(async () => (await snapshot(page)).rendering.paused).toBe(false)
})

test('Scene API freezes the final frame, starts with zero delta and survives early pause/dispose', async ({ page }) => {
  await page.goto('/?mode=static')
  const result = await page.evaluate(async () => {
    const path = '/src/three/Scene.ts'
    const { mountScene } = await import(/* @vite-ignore */ path)
    const configPath = '/src/three/config/sections.ts'
    const { heroState } = await import(/* @vite-ignore */ configPath)
    let source = structuredClone(heroState)
    const host = document.createElement('div')
    host.style.cssText = 'position:fixed;inset:0;width:320px;height:240px'
    document.body.append(host)
    const scene = mountScene(host, { stateSource: () => source })
    scene.pause()
    await scene.ready
    const initiallyPaused = scene.inspect().rendering
    const firstFrame = () => new Promise<any>((resolve) => {
      const before = scene.inspect().rendering.frames
      const check = () => {
        if (scene.inspect().rendering.frames > before) resolve(scene.inspect())
        else requestAnimationFrame(check)
      }
      requestAnimationFrame(check)
    })
    scene.resume()
    const started = await firstFrame()
    const nextState = structuredClone(started.state)
    nextState.rotation[1] = 42
    source = nextState // A pending scroll update must be sampled by the final frame.
    scene.pause()
    const stopped = scene.inspect()
    scene.pause()
    const stoppedAgain = scene.inspect()
    await new Promise((resolve) => setTimeout(resolve, 250))
    scene.resume()
    const resumed = await firstFrame()
    scene.dispose()
    scene.resume()
    scene.pause()
    const disposedFrames = scene.inspect().rendering.frames
    await new Promise((resolve) => setTimeout(resolve, 100))
    const disposedAfter = scene.inspect().rendering.frames
    const late = mountScene(host)
    late.dispose()
    await late.ready
    late.resume()
    const lateFrames = late.inspect().rendering.frames
    const canvases = host.querySelectorAll('canvas').length
    host.remove()
    return { initiallyPaused, started, stopped, stoppedAgain, resumed, disposedFrames, disposedAfter, lateFrames, canvases }
  })
  expect(result.initiallyPaused).toMatchObject({ paused: true, frames: 0, waterTime: 0 })
  expect(result.started.rendering.lastDelta).toBe(0)
  expect(result.stopped.rendering.frames).toBe(result.started.rendering.frames + 1)
  expect(result.stopped.rendering.waterTime).toBe(result.started.rendering.waterTime)
  expect(result.stopped.rotation[1]).toBeCloseTo(42 * Math.PI / 180)
  expect(result.stoppedAgain).toEqual(result.stopped)
  expect(result.resumed.rendering.lastDelta).toBe(0)
  expect(result.resumed.rendering.waterTime).toBe(result.stopped.rendering.waterTime)
  expect(result.resumed.parts).toEqual(result.stopped.parts)
  expect(result.disposedAfter).toBe(result.disposedFrames)
  expect(result.lateFrames).toBe(0)
  expect(result.canvases).toBe(0)
})

test('initially hidden load stays paused; manual gate and disposed observers cannot resume', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' })
  })
  await page.goto('/?mode=live&inspect')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'ready')
  expect((await frozen(page)).rendering.frames).toBe(0)
  await visibility(page, 'visible')
  await expect.poll(async () => (await snapshot(page)).rendering.frames).toBeGreaterThan(0)
  const calls = await page.evaluate(async () => {
    const path = '/src/three/VisibilityController.ts'
    const { VisibilityController } = await import(/* @vite-ignore */ path)
    const calls: string[] = []
    const controller = new VisibilityController([document.querySelector('[data-has-3d]')!], {
      pause: () => calls.push('pause'), resume: () => calls.push('resume'),
    })
    const set = (value: string) => {
      Object.defineProperty(document, 'visibilityState', { configurable: true, value })
      document.dispatchEvent(new Event('visibilitychange'))
    }
    controller.pause()
    set('hidden')
    set('visible')
    await new Promise((resolve) => setTimeout(resolve, 100))
    const manual = [...calls]
    controller.resume()
    controller.dispose()
    controller.dispose()
    set('hidden')
    controller.pause()
    controller.resume()
    await new Promise((resolve) => setTimeout(resolve, 100))
    set('visible')
    return { manual, final: calls }
  })
  expect(calls.manual).toEqual(['resume', 'pause'])
  expect(calls.final).toEqual(['resume', 'pause', 'resume'])
})
