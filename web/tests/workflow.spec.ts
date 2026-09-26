import { expect, test } from '@playwright/test'

const png = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAAO0lEQVR4nO3RsREAMAjDQJNt02QDds8IoqHTD2DuRL2+2XRW1+OBAX+ATIRMhEyETIRMhEyETIRMFPIBqPwBlDPvuzIAAAAASUVORK5CYII=',
  'base64',
)

test('upload → durable demo task → actual GLB rendering → reload', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  await page.goto('/')
  await page.getByRole('textbox', { name: '專案名稱' }).fill('瀏覽器完整流程')
  const createResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/projects') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: '建立專案', exact: true }).click()
  const project = await (await createResponse).json()
  await expect(page).toHaveURL(new RegExp(project.id))

  const uploadResponse = page.waitForResponse(
    (response) => response.url().includes('/images') && response.request().method() === 'POST',
  )
  await page.getByLabel('上傳圖片', { exact: true }).setInputFiles({
    name: 'product.png',
    mimeType: 'image/png',
    buffer: png,
  })
  expect((await uploadResponse).ok()).toBeTruthy()

  const generationResponse = page.waitForResponse(
    (response) => response.url().endsWith('/generations') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: '開始示範生成', exact: true }).click()
  const generation = await (await generationResponse).json()
  expect(generation.provider).toBe('fake')
  // Refresh while the worker runs: selected project and task must come from persistence.
  await page.reload()
  await expect(page.getByTestId('model-ready')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByTestId('model-canvas')).toBeVisible()
  const result = await page.request.get(`/api/generations/${generation.id}`)
  const task = await result.json()
  expect(task.state).toBe('ready')
  const version = await (
    await page.request.get(`/api/model-versions/${task.model_version_id}`)
  ).json()
  const model = await page.request.get(version.asset_url)
  expect(model.headers()['content-type']).toContain('model/gltf-binary')
  expect((await model.body()).subarray(0, 4).toString()).toBe('glTF')

  await page.reload()
  await expect(page.getByTestId('model-ready')).toBeVisible()
  await page.screenshot({ path: test.info().outputPath('workspace.png'), fullPage: true })
  expect(pageErrors).toEqual([])
})

test('corrupt image is rejected before generation and UI recovers', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('textbox', { name: '專案名稱' }).fill('圖片驗證')
  await page.getByRole('button', { name: '建立專案', exact: true }).click()
  await expect(page).toHaveURL(/project=/)
  const response = page.waitForResponse(
    (response) => response.url().includes('/images') && response.request().method() === 'POST',
  )
  await page.getByLabel('上傳圖片', { exact: true }).setInputFiles({
    name: 'broken.png',
    mimeType: 'image/png',
    buffer: Buffer.from('not an image'),
  })
  expect((await response).status()).toBe(400)
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByRole('button', { name: '開始示範生成', exact: true })).toBeDisabled()
  const retry = page.waitForResponse(
    (response) => response.url().includes('/images') && response.request().method() === 'POST',
  )
  await page.getByLabel('上傳圖片', { exact: true }).setInputFiles({
    name: 'correct.png',
    mimeType: 'image/png',
    buffer: png,
  })
  expect((await retry).ok()).toBeTruthy()
  await expect(page.getByRole('button', { name: '開始示範生成', exact: true })).toBeEnabled()
})
