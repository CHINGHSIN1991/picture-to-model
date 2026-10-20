import { Box3, BufferGeometry, Material, Mesh, Object3D, Texture, Vector3 } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

export async function loadModel() {
  const { scene: model } = await new GLTFLoader().loadAsync(`${import.meta.env.BASE_URL}models/reef.glb`)
  const bounds = new Box3().setFromObject(model)
  if (bounds.isEmpty()) {
    disposeModel(model)
    throw new Error('The GLB contains no visible geometry.')
  }
  const center = bounds.getCenter(new Vector3())
  // Move only the loader's wrapper, preserving authored pivots and local transforms.
  model.position.sub(center)
  model.updateMatrixWorld(true)
  const hierarchy: { name: string; parent: string | null; vertices: number; triangles: number }[] = []
  model.traverse((object) => {
    const mesh = object as Mesh
    const vertices = mesh.isMesh ? mesh.geometry.attributes.position!.count : 0
    const triangles = mesh.isMesh ? (mesh.geometry.index?.count ?? vertices) / 3 : 0
    if (mesh.isMesh) {
      mesh.castShadow = object.name !== 'Sand'
      mesh.receiveShadow = true
    }
    if (object !== model) {
      hierarchy.push({ name: object.name, parent: object.parent === model ? null : object.parent?.name ?? null, vertices, triangles })
    }
  })
  console.groupCollapsed('[reef-viewer] Model hierarchy')
  console.table(hierarchy)
  console.groupEnd()
  // Serializable evidence for browser inspection, without exposing mutable scene objects.
  console.info('[reef-viewer] hierarchy', JSON.stringify(hierarchy))
  return { model, center, bounds: new Box3().setFromObject(model) }
}

export function disposeModel(model: Object3D) {
  const geometries = new Set<BufferGeometry>()
  const materials = new Set<Material>()
  const textures = new Set<Texture>()
  model.traverse((object) => {
    const mesh = object as Mesh
    if (!mesh.isMesh) return
    geometries.add(mesh.geometry)
    for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
      materials.add(material)
      for (const value of Object.values(material)) {
        if (value instanceof Texture) textures.add(value)
      }
    }
  })
  geometries.forEach((geometry) => geometry.dispose())
  materials.forEach((material) => material.dispose())
  textures.forEach((texture) => {
    texture.dispose()
    const image = texture.source.data
    if (typeof ImageBitmap !== 'undefined' && image instanceof ImageBitmap) image.close()
  })
}
