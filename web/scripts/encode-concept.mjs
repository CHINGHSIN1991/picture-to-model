// Re-encode the existing concept at its original dimensions; no composition changes.
import { chromium } from '@playwright/test'
import { readFile, writeFile } from 'node:fs/promises'
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome' })
try {
  const page = await browser.newPage()
  const source = await readFile(new URL('../src/assets/final-concept-800.jpg', import.meta.url))
  const result = await page.evaluate(async (data) => {
    const image = new Image(); image.src = `data:image/jpeg;base64,${data}`; await image.decode()
    const canvas = document.createElement('canvas'); canvas.width = image.naturalWidth; canvas.height = image.naturalHeight
    canvas.getContext('2d').drawImage(image, 0, 0)
    return canvas.toDataURL('image/webp', 0.85)
  }, source.toString('base64'))
  const bytes = Buffer.from(result.split(',')[1], 'base64')
  await writeFile(new URL('../src/assets/final-concept-800.webp', import.meta.url), bytes)
  console.log(JSON.stringify({ originalBytes: source.length, webpBytes: bytes.length, quality: 0.85 }))
} finally { await browser.close() }
