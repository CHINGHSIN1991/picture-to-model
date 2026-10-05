import { expect, test, type Page } from '@playwright/test'

const png = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAAO0lEQVR4nO3RsREAMAjDQJNt02QDds8IoqHTD2DuRL2+2XRW1+OBAX+ATIRMhEyETIRMhEyETIRMFPIBqPwBlDPvuzIAAAAASUVORK5CYII=',
  'base64',
)

async function createReadyProject(page: Page, name: string) {
  const project = await (await page.request.post('/api/projects', { data: { name } })).json()
  const source = await (
    await page.request.post(`/api/projects/${project.id}/images`, {
      multipart: { file: { name: 'product.png', mimeType: 'image/png', buffer: png } },
    })
  ).json()
  const generation = await (
    await page.request.post(`/api/projects/${project.id}/generations`, {
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      data: { source_asset_id: source.id },
    })
  ).json()
  await expect
    .poll(async () => {
      const task = await (await page.request.get(`/api/generations/${generation.id}`)).json()
      return task.state
    })
    .toBe('ready')
  const task = await (await page.request.get(`/api/generations/${generation.id}`)).json()
  const version = await (
    await page.request.get(`/api/model-versions/${task.model_version_id}`)
  ).json()
  return { project, generation, version }
}

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

test('failed GLB load stays unready and retries without creating a generation', async ({
  page,
}) => {
  const { project, version } = await createReadyProject(page, '預覽失敗恢復')
  const modelUrl = `**${version.asset_url}`
  await page.route(modelUrl, (route) =>
    route.fulfill({ status: 503, body: 'temporarily unavailable' }),
  )
  await page.goto(`/?project=${project.id}`)
  await expect(page.getByRole('alert')).toContainText('模型載入失敗')
  await expect(page.getByTestId('model-ready')).toHaveCount(0)
  await page.unroute(modelUrl)
  await page.getByRole('button', { name: '重新載入預覽' }).click()
  await expect(page.getByTestId('model-ready')).toBeVisible()
  const detail = await (await page.request.get(`/api/projects/${project.id}`)).json()
  expect(detail.generations).toHaveLength(1)

  await page.getByRole('button', { name: '← 所有專案' }).click()
  await expect(page).not.toHaveURL(/project=/)
  await page.getByRole('button', { name: /預覽失敗恢復.*已有參考圖片/ }).click()
  await expect(page.getByTestId('model-ready')).toBeVisible()
  await expect(page.getByTestId('model-canvas')).toHaveCount(1)
  await page.setViewportSize({ width: 390, height: 844 })
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    .toBeTruthy()
  await page.screenshot({ path: test.info().outputPath('mobile-workspace.png'), fullPage: true })
})

test('interrupted status polling reconnects to the existing task', async ({ page }) => {
  const { project, generation } = await createReadyProject(page, '進度斷線恢復')
  // Present an in-flight snapshot once; the durable server task is already complete.
  await page.route(`**/api/projects/${project.id}`, async (route) => {
    const response = await route.fetch()
    const detail = await response.json()
    detail.generations[0].state = 'generating'
    detail.generations[0].model_version_id = null
    await route.fulfill({ response, json: detail })
  })
  const taskUrl = `**/api/generations/${generation.id}`
  await page.route(taskUrl, (route) => route.abort())
  await page.goto(`/?project=${project.id}`)
  await expect(page.getByRole('alert')).toContainText('重新連線')
  await page.unroute(taskUrl)
  await expect(page.getByTestId('model-ready')).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
  const detail = await (await page.request.get(`/api/projects/${project.id}`)).json()
  expect(detail.generations).toHaveLength(1)
})
