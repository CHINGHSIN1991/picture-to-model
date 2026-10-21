import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'

const bytes = readFileSync(new URL('../../export/reef.glb', import.meta.url))
const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString('utf8'))
const checksum = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex')

test('loads the audited GLB, preserves hierarchy and supports orbit, zoom and resize', async ({ page }, testInfo) => {
  const errors: string[] = []
  let hierarchy: { name: string; parent: string | null; vertices: number; triangles: number }[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
    if (message.text().startsWith('[reef-viewer] hierarchy ')) {
      hierarchy = JSON.parse(message.text().slice('[reef-viewer] hierarchy '.length))
    }
  })
  const response = page.waitForResponse((response) => response.url().endsWith('/models/reef.glb'))
  // Isolate camera movement from the animated water when comparing screenshots.
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/viewer.html')
  expect(checksum(await (await response).body())).toBe(checksum(bytes))
  await expect(page.locator('main')).toHaveAttribute('data-state', 'ready')
  expect(hierarchy).toHaveLength(gltf.nodes.length)
  for (const [index, node] of gltf.nodes.entries()) {
    const parent = gltf.nodes.find((candidate: { children?: number[] }) => candidate.children?.includes(index))
    expect(hierarchy.find((entry) => entry.name === node.name)?.parent).toBe(parent?.name ?? null)
  }
  expect(hierarchy.filter((entry) => entry.vertices > 0)).toHaveLength(91)
  expect(hierarchy.reduce((sum, entry) => sum + entry.triangles, 0)).toBe(49420)
  await testInfo.attach('hierarchy', { body: JSON.stringify(hierarchy, null, 2), contentType: 'application/json' })
  const canvas = page.locator('canvas')
  await page.waitForTimeout(700)
  const hero = await canvas.screenshot({ path: testInfo.outputPath('hero.png') })
  await page.mouse.move(520, 380)
  await page.mouse.down()
  await page.mouse.move(800, 390, { steps: 20 })
  await page.mouse.up()
  await page.waitForTimeout(700)
  const orbit = await canvas.screenshot({ path: testInfo.outputPath('orbit.png') })
  expect(checksum(orbit)).not.toBe(checksum(hero))
  await page.mouse.wheel(0, -240)
  await page.waitForTimeout(700)
  const zoom = await canvas.screenshot()
  expect(checksum(zoom)).not.toBe(checksum(orbit))
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(canvas).toHaveJSProperty('width', 390)
  await expect(canvas).toHaveJSProperty('height', 844)
  await page.reload()
  await expect(page.locator('main')).toHaveAttribute('data-state', 'ready')
  await page.waitForTimeout(700)
  await page.screenshot({ path: testInfo.outputPath('mobile.png') })
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
  expect(errors).toEqual([])
})

test('caps rendering resolution on a high-DPR screen', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3 })
  const page = await context.newPage()
  await page.goto('http://127.0.0.1:4173/viewer.html')
  await expect(page.locator('main')).toHaveAttribute('data-state', 'ready')
  await expect(page.locator('canvas')).toHaveJSProperty('width', 585)
  await expect(page.locator('canvas')).toHaveJSProperty('height', 1266)
  await context.close()
})

test('shows an actionable message when the GLB request fails', async ({ page }) => {
  await page.route('**/models/reef.glb', (route) => route.fulfill({ status: 404, body: 'Not found' }))
  await page.goto('/viewer.html')
  await expect(page.getByRole('alert')).toContainText('無法顯示模型')
  await expect(page.locator('main')).toHaveAttribute('data-state', 'error')
  await expect(page.locator('canvas')).toHaveCount(0)
})

test('shows an actionable message when WebGL is unavailable', async ({ page }) => {
  await page.addInitScript(() => {
    const getContext = HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = function (type: string, ...args: unknown[]) {
      if (type.startsWith('webgl')) return null
      return getContext.apply(this, [type, ...args] as Parameters<typeof getContext>)
    } as typeof getContext
  })
  await page.goto('/viewer.html')
  await expect(page.getByRole('alert')).toContainText('WebGL')
  await expect(page.locator('main')).toHaveAttribute('data-state', 'error')
})
