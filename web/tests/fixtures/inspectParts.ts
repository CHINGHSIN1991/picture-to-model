import { Matrix4, PerspectiveCamera, Scene, Vector3 } from 'three'
import { loadModel } from '../../src/three/Model'
import { PartAnimator } from '../../src/three/PartAnimator'
import { partAnimations } from '../../src/three/config/partAnimations'
import { createRenderer } from '../../src/three/createRenderer'
import { createLighting } from '../../src/three/createLighting'
import { createWaterMaterials } from '../../src/three/createWaterMaterials'

export async function inspectParts() {
  const model = await loadModel('/models/reef.glb')
  const scene = new Scene()
  const renderer = createRenderer()
  renderer.setSize(800, 600)
  renderer.setPixelRatio(1)
  const lighting = createLighting(scene, renderer)
  const water = createWaterMaterials(model.scene, lighting.config)
  water.apply()
  const camera = new PerspectiveCamera(35, 800 / 600, 0.01, 100)
  camera.position.set(-1, 3, 7)
  camera.lookAt(new Vector3(0, 0.8, 0))
  scene.add(model.root)
  const capture = () => {
    renderer.shadowMap.needsUpdate = true
    renderer.render(scene, camera)
    const gl = renderer.getContext()
    const bytes = new Uint8Array(800 * 600 * 4)
    gl.readPixels(0, 0, 800, 600, gl.RGBA, gl.UNSIGNED_BYTE, bytes)
    return { calls: renderer.info.render.calls, triangles: renderer.info.render.triangles, pixels: renderer.domElement.toDataURL(), bytes }
  }
  const snapshot = () => Object.fromEntries(Object.entries(model.parts).map(([name, node]) => {
    node.updateMatrix()
    return [name, node.matrix.toArray()]
  }))
  const before = capture()
  const rest = snapshot()
  const report = model.buildInstances()
  const after = capture()
  const pixelMeanAbsoluteError = after.bytes.reduce((sum, value, i) => sum + Math.abs(value - before.bytes[i]!), 0) / after.bytes.length
  let matrixError = 0
  model.scene.traverse((node: any) => {
    if (!node.isInstancedMesh) return
    const sources = Object.values(model.groups).flat().filter((source: any) => !source.visible && source.parent === node.parent && source.geometry === node.geometry && source.material === node.material)
    sources.forEach((source, index) => {
      const matrix = new Matrix4()
      node.getMatrixAt(index, matrix)
      matrix.elements.forEach((value, i) => { matrixError = Math.max(matrixError, Math.abs(value - source.matrix.elements[i]!)) })
    })
  })
  const animator = new PartAnimator(model)
  const all = { rocks: 1, boulders: 0, corals: 1, kelp: 1, fish: 1, diver: 1 }
  animator.setProgress(all)
  animator.update(0, true)
  const departed = snapshot()
  const hidden = Object.fromEntries(Object.entries(model.groups).map(([name, nodes]) => [name, nodes.every((node) => node.scale.length() === 0)]))
  animator.setProgress({ ...all, rocks: 0, corals: 0, kelp: 0, fish: 0, diver: 0 })
  animator.update(0.1)
  const intermediate = snapshot()
  const coralScales = model.groups.corals.map((node) => node.scale.length())
  animator.setProgress({ corals: 0.5 })
  animator.update(0, true)
  const stagger = { hidden: model.groups.corals.filter((node) => node.scale.length() === 0).length, total: model.groups.corals.length }
  animator.setProgress({ corals: 0 })
  animator.update(0, true)
  const restored = snapshot()
  const restoredPixels = capture().pixels
  // Same nodes/config interface with a different mode; no scroll code changes.
  const alternative = new PartAnimator(model, { ...partAnimations, corals: { mode: 'explode', center: [0, 0.8, 0], distance: 0.5, spring: 6 } })
  alternative.setProgress({ corals: 1 })
  alternative.update(0, true)
  const swapped = snapshot()
  const result = {
    before: { calls: before.calls, triangles: before.triangles }, after: { calls: after.calls, triangles: after.triangles },
    report, matrixError, samePixels: before.pixels === after.pixels, restoredPixels: after.pixels === restoredPixels,
    pixelMeanAbsoluteError, comparison: { before: before.pixels, after: after.pixels },
    rest, departed, intermediate, restored, hidden, coralScales, stagger, swapped,
  }
  model.dispose()
  lighting.dispose()
  renderer.dispose()
  return result
}
