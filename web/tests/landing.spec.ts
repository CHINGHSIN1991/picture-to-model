import { expect, test } from '@playwright/test'
import { createHash } from 'node:crypto'

// mockups/SECTIONS.md: six sections, in order, each with its own component and heading.
const sections = [
  { id: 'hero', heading: '一張圖,變成會動的3D 網站' },
  { id: 'upload', heading: '從一張圖開始' },
  { id: 'model', heading: '每個零件都是程式碼' },
  { id: 'controls', heading: '材質、光線、相機,全是設定檔' },
  { id: 'interaction', heading: '放進網站,就會動' },
  { id: 'cta', heading: '用你的下一張圖試試看' },
]
const checksum = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex')

test('renders every section over one fixed, non-interactive canvas with the model in its hero state', async ({ browser }, testInfo) => {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()
  const errors: string[] = []
  let model: { nodes: number; groups: Record<string, number> } | undefined
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
    if (message.text().startsWith('[reef-landing] model ')) model = JSON.parse(message.text().slice('[reef-landing] model '.length))
  })
  // Reduced motion keeps the frame deterministic; `mode=live` keeps the scene (Step 14 would serve a still).
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/?mode=live')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'ready')
  // One live Three.js canvas, fixed behind the page, never intercepting pointer events.
  await expect(page.locator('canvas')).toHaveCount(1)
  const stage = page.locator('.stage')
  await expect(stage).toHaveCSS('position', 'fixed')
  await expect(stage).toHaveCSS('pointer-events', 'none')
  expect(model).toEqual({ nodes: 95, groups: { rocks: 7, boulders: 12, corals: 35, kelp: 16, fish: 15, diver: 1 } })
  // Every SECTIONS.md section exists, in order, with real copy.
  const ids = await page.locator('main section').evaluateAll((nodes) => nodes.map((node) => node.id))
  expect(ids).toEqual(sections.map((section) => section.id))
  for (const section of sections) {
    const heading = page.locator(`#${section.id} h1, #${section.id} h2`)
    expect((await heading.innerText()).replace(/\s+/g, '')).toBe(section.heading.replace(/\s+/g, ''))
  }
  await expect(page.locator('#upload img')).toBeVisible()
  await expect(page.locator('#controls .prop.panel')).toContainText('曝光')
  await page.waitForTimeout(500)
  await page.screenshot({ path: testInfo.outputPath('hero.png') })
  const buffer = await page.locator('canvas').evaluate((canvas: HTMLCanvasElement) => [canvas.width, canvas.height])
  // Scrolling moves the sections, not the canvas (element screenshots include the DOM above it, so compare geometry).
  await page.locator('#cta').scrollIntoViewIfNeeded()
  await page.waitForTimeout(300)
  expect(await stage.boundingBox()).toMatchObject({ x: 0, y: 0, width: 1440, height: 900 })
  expect((await page.locator('#hero').boundingBox())!.y).toBeLessThan(0)
  expect(await page.locator('canvas').evaluate((canvas: HTMLCanvasElement) => [canvas.width, canvas.height])).toEqual(buffer)
  await page.screenshot({ path: testInfo.outputPath('cta.png') })
  // Nav links reach their sections.
  await page.locator('.nav a', { hasText: '調光' }).click()
  await expect.poll(async () => (await page.locator('#controls').boundingBox())!.y).toBeLessThan(2)
  expect(errors).toEqual([])
  await context.close()
})

test('applies another section state on request and keeps the layout within a phone viewport', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/?mode=live')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'ready')
  await page.waitForTimeout(400)
  const hero = checksum(await page.locator('canvas').screenshot())
  await page.goto('/?state=3&mode=live')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'ready')
  await page.waitForTimeout(400)
  expect(checksum(await page.locator('canvas').screenshot())).not.toBe(hero)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.waitForTimeout(300)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
  await expect(page.locator('canvas')).toHaveJSProperty('width', 390)
  await context.close()
})

test('shows an actionable message when the GLB request fails', async ({ page }) => {
  await page.route('**/models/reef.glb', (route) => route.fulfill({ status: 404, body: 'Not found' }))
  await page.goto('/')
  await expect(page.getByRole('alert')).toContainText('3D 場景無法顯示')
  await expect(page.locator('.site')).toHaveAttribute('data-state', 'error')
  await expect(page.locator('canvas')).toHaveCount(0)
  // The copy still reads without the scene.
  await expect(page.locator('#cta h2')).toBeVisible()
})
