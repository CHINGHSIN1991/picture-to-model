import { expect, test } from '@playwright/test'

for (const entry of [
  { name: 'landing', url: '/?mode=live&inspect', ready: '.site', container: '.stage' },
  { name: 'viewer', url: '/viewer.html', ready: 'main', container: 'main' },
]) {
  test(`${entry.name} caps DPR on load, CSS resize and repeated DPR-only display changes`, async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 800, height: 600 }, deviceScaleFactor: 2 })
    const page = await context.newPage()
    const errors: string[] = []
    page.on('pageerror', (error) => errors.push(error.message))
    try {
      await page.goto(`http://127.0.0.1:4173${entry.url}`)
      await expect(page.locator(entry.ready)).toHaveAttribute('data-state', 'ready')
      const canvas = page.locator('canvas')
      await expect(canvas).toHaveJSProperty('width', 1200)
      await expect(canvas).toHaveJSProperty('height', 900)
      expect(await canvas.evaluate((node: HTMLCanvasElement) => node.getContext('webgl2')!.getContextAttributes()!.antialias)).toBe(true)
      // Keep CSS geometry constant: no synthetic resize event or DPR getter override.
      const cdp = await context.newCDPSession(page)
      let media = ''
      await page.evaluate(() => {
        ;(window as any).__resizeEvents = 0
        window.addEventListener('resize', () => (window as any).__resizeEvents++)
      })
      for (const [dpr, width, height] of [[3, 1200, 900], [1, 800, 600], [1.25, 1000, 750], [0.75, 600, 450], [2, 1200, 900]]) {
        await cdp.send('Emulation.setDeviceMetricsOverride', { width: 800, height: 600, deviceScaleFactor: dpr, mobile: false })
        await expect.poll(() => page.evaluate(() => devicePixelRatio)).toBe(dpr)
        // CDP changes DPR but does not invalidate existing media queries by itself.
        // Toggle the media override (both resolve to screen) to request reevaluation.
        media = media ? '' : 'screen'
        await cdp.send('Emulation.setEmulatedMedia', { media })
        await expect(canvas).toHaveJSProperty('width', width)
        await expect(canvas).toHaveJSProperty('height', height)
      }
      expect(await page.evaluate(() => (window as any).__resizeEvents)).toBe(0)
      // Resize at DPR 3; odd CSS sizes exercise integer buffer rounding.
      await cdp.send('Emulation.setDeviceMetricsOverride', { width: 801, height: 601, deviceScaleFactor: 3, mobile: false })
      await expect(canvas).toHaveJSProperty('width', 1201)
      await expect(canvas).toHaveJSProperty('height', 901)
      // ResizeObserver must also handle container-only changes.
      await page.locator(entry.container).evaluate((node: HTMLElement) => {
        node.style.width = '501px'
        node.style.height = '401px'
      })
      await expect(canvas).toHaveJSProperty('width', 751)
      await expect(canvas).toHaveJSProperty('height', 601)
      expect(await canvas.evaluate((node) => [node.clientWidth, node.clientHeight])).toEqual([501, 401])
      expect(errors).toEqual([])
    } finally {
      await context.close()
    }
  })
}

test('DPR observation cleans up after disposal and does not restart a paused scene', async ({ page, context }) => {
  await page.goto('/?mode=static')
  await page.evaluate(async () => {
    const path = '/src/three/Scene.ts'
    const { mountScene } = await import(/* @vite-ignore */ path)
    const host = document.createElement('div')
    host.style.cssText = 'position:fixed;inset:0;width:320px;height:240px'
    document.body.append(host)
    const scene = mountScene(host)
    scene.pause()
    await scene.ready
    const helperPath = '/src/three/rendererResolution.ts'
    const { observePixelRatio } = await import(/* @vite-ignore */ helperPath)
    ;(window as any).__resolution = { scene, canvas: host.querySelector('canvas'), changes: 0,
      stop: observePixelRatio(() => (window as any).__resolution.changes++) }
  })
  const cdp = await context.newCDPSession(page)
  let media = ''
  const change = async (dpr: number) => {
    await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1024, height: 768, deviceScaleFactor: dpr, mobile: false })
    media = media ? '' : 'screen'
    await cdp.send('Emulation.setEmulatedMedia', { media })
  }
  await change(2)
  await expect.poll(() => page.evaluate(() => (window as any).__resolution.canvas.width)).toBe(480)
  expect(await page.evaluate(() => (window as any).__resolution.scene.inspect().rendering)).toMatchObject({ paused: true, frames: 0 })
  await expect.poll(() => page.evaluate(() => (window as any).__resolution.changes)).toBe(1)
  await page.evaluate(() => {
    const { stop, scene } = (window as any).__resolution
    stop(); stop(); scene.dispose()
  })
  await change(1)
  await page.waitForTimeout(150)
  expect(await page.evaluate(() => {
    const { changes, canvas, scene } = (window as any).__resolution
    return { changes, width: canvas.width, frames: scene.inspect().rendering.frames }
  })).toEqual({ changes: 1, width: 480, frames: 0 })
})
