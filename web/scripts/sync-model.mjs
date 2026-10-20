import { copyFile, mkdir } from 'node:fs/promises'

const source = new URL('../../export/reef.glb', import.meta.url)
const target = new URL('../public/models/reef.glb', import.meta.url)

try {
  await mkdir(new URL('.', target), { recursive: true })
  await copyFile(source, target)
  console.log('Synced export/reef.glb → public/models/reef.glb')
} catch (error) {
  console.error('Cannot copy export/reef.glb. Complete Step 06 before starting the viewer.')
  console.error(error.message)
  process.exitCode = 1
}
