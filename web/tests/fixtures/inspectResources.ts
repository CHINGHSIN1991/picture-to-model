import { Mesh, Texture, PerspectiveCamera, type Material } from 'three'
import { loadModel } from '../../src/three/Model'
import { createScene } from '../../src/three/createScene'
import { createRenderer } from '../../src/three/createRenderer'
import { createLighting } from '../../src/three/createLighting'
import { createWaterMaterials } from '../../src/three/createWaterMaterials'

/** Count model and generated resources separately, using the landing material setup. */
export async function inspectResources() {
  const renderer = createRenderer()
  renderer.setSize(800, 600)
  const scene = createScene(), lighting = createLighting(scene, renderer)
  const model = await loadModel('/models/reef.glb')
  createWaterMaterials(model.scene, lighting.config).apply()
  const instances = model.buildInstances()
  scene.add(model.root)
  const camera = new PerspectiveCamera(35, 800 / 600, 0.01, 100)
  camera.position.set(-1, 3, 7); camera.lookAt(0, 0.8, 0)
  renderer.render(scene, camera)
  const modelMaterials = new Set<Material>(), sceneMaterials = new Set<Material>(), textures = new Set<Texture>()
  model.scene.traverse((node) => {
    if (!(node instanceof Mesh)) return
    for (const material of Array.isArray(node.material) ? node.material : [node.material]) modelMaterials.add(material)
  })
  scene.traverse((node) => {
    if (!(node instanceof Mesh)) return
    for (const material of Array.isArray(node.material) ? node.material : [node.material]) {
      sceneMaterials.add(material)
      Object.values(material).forEach((value) => { if (value instanceof Texture) textures.add(value) })
    }
  })
  const shadows: number[][] = []
  scene.traverse((node: any) => { if (node.shadow?.map) shadows.push([node.shadow.map.width, node.shadow.map.height]) })
  const result = { instances, modelMaterials: modelMaterials.size, sceneMeshMaterials: sceneMaterials.size,
    modelTextures: [...textures].map((texture) => ({ name: texture.name, width: texture.image.width, height: texture.image.height })),
    environment: { width: scene.environment!.image.width, height: scene.environment!.image.height }, shadows,
    rendererMemory: { ...renderer.info.memory }, programs: renderer.info.programs?.length }
  model.dispose(); lighting.dispose(); renderer.dispose()
  return result
}
