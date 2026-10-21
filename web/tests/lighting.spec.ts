import { expect, test } from '@playwright/test'
import { createHash } from 'node:crypto'

const checksum = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex')

test('keeps debug tools out of the normal viewer and respects reduced motion', async ({ page }) => {
  const requests: string[] = []
  page.on('request', (request) => requests.push(request.url()))
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/viewer.html')
  await expect(page.locator('main')).toHaveAttribute('data-state', 'ready')
  await expect(page.locator('[data-lighting-debug]')).toHaveCount(0)
  await expect(page.locator('[data-lighting-stats]')).toHaveCount(0)
  expect(requests.some((url) => /createLightingDebug|lil-gui|stats\.js/.test(url))).toBe(false)
  await page.waitForTimeout(300)
  const frozen = checksum(await page.locator('canvas').screenshot())
  await page.waitForTimeout(400)
  expect(checksum(await page.locator('canvas').screenshot())).toBe(frozen)
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await page.waitForTimeout(700)
  expect(checksum(await page.locator('canvas').screenshot())).not.toBe(frozen)
})

test('edits lighting live, exports plain JSON and restores the preset', async ({ page }, testInfo) => {
  const errors: string[] = []
  const configs: Record<string, unknown>[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
    const prefix = '[reef-viewer] lightingConfig '
    if (message.text().startsWith(prefix)) configs.push(JSON.parse(message.text().slice(prefix.length)))
  })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/viewer.html?debug')
  await expect(page.locator('main')).toHaveAttribute('data-state', 'ready')
  await expect(page.locator('[data-lighting-debug]')).toBeVisible()
  await expect(page.locator('[data-lighting-stats]')).toBeVisible()
  await page.getByRole('button', { name: '輸出設定至 Console', exact: true }).click()
  await expect.poll(() => configs.length).toBe(1)
  // Inspect pixels away from the GUI so changing a text field cannot pass this check.
  const clip = { x: 100, y: 250, width: 500, height: 400 }
  const before = checksum(await page.screenshot({ clip }))
  const exposure = page.getByRole('textbox', { name: '曝光', exact: true })
  await exposure.fill('0.4')
  await exposure.press('Enter')
  await page.waitForTimeout(200)
  expect(checksum(await page.screenshot({ clip }))).not.toBe(before)
  await page.getByRole('button', { name: '輸出設定至 Console', exact: true }).click()
  await expect.poll(() => configs.length).toBe(2)
  expect(configs[1]!.exposure).toBe(0.4)
  await page.getByRole('button', { name: '還原設定', exact: true }).click()
  await page.getByRole('button', { name: '輸出設定至 Console', exact: true }).click()
  await expect.poll(() => configs.length).toBe(3)
  expect(configs[2]).toEqual(configs[0])
  await page.screenshot({ path: testInfo.outputPath('lighting-debug.png') })
  expect(errors).toEqual([])
})

test('releases lighting resources and debug overlays when the viewer is disposed', async ({ page }) => {
  await page.goto('/viewer.html')
  await expect(page.locator('main')).toHaveAttribute('data-state', 'ready')
  const result = await page.evaluate(async () => {
    // Exercise the independent Three.js lifecycle, as Vue does during unmount.
    const modulePath = '/src/three/Viewer.ts'
    const { mountViewer } = await import(/* @vite-ignore */ modulePath)
    history.replaceState(null, '', '/viewer.html?debug')
    const container = document.createElement('div')
    container.style.cssText = 'position:fixed;inset:0;width:600px;height:400px'
    document.body.append(container)
    const viewer = mountViewer(container)
    await viewer.ready
    const mounted = document.querySelectorAll('[data-lighting-debug]').length
    viewer.dispose()
    viewer.dispose()
    const result = {
      mounted,
      canvas: container.querySelectorAll('canvas').length,
      gui: document.querySelectorAll('[data-lighting-debug]').length,
      stats: document.querySelectorAll('[data-lighting-stats]').length,
    }
    container.remove()
    return result
  })
  expect(result).toEqual({ mounted: 1, canvas: 0, gui: 0, stats: 0 })
})
