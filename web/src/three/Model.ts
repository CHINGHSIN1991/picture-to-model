import { Box3, BufferGeometry, Color, Group, Material, Mesh, MeshStandardMaterial, Object3D, Texture } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { partGroupNames, partGroups, type PartGroup } from './config/partGroups'

export interface Model {
  /** Transform target for sections (position / rotation / scale). Authored origin = reef base centre. */
  root: Group
  /** The GLB scene, untouched: authored pivots and local transforms are preserved for Step 13. */
  scene: Group
  /** Every named node, by MODEL_PLAN name. */
  parts: Record<string, Object3D>
  /** PROJECT_SPEC part groups. Plain meshes for now; Step 13 may swap instancing groups for InstancedMesh. */
  groups: Record<PartGroup, Object3D[]>
  bounds: Box3
  setMaterialParam(name: string, key: string, value: number | string): void
  dispose(): void
}

export async function loadModel(url: string): Promise<Model> {
  const { scene } = await new GLTFLoader().loadAsync(url)
  const bounds = new Box3().setFromObject(scene)
  if (bounds.isEmpty()) {
    disposeObject(scene)
    throw new Error('The GLB contains no visible geometry.')
  }
  const root = new Group()
  root.name = 'Model_Root'
  root.add(scene)
  const parts: Record<string, Object3D> = {}
  const groups = Object.fromEntries(partGroupNames.map((name) => [name, [] as Object3D[]])) as Record<PartGroup, Object3D[]>
  const patterns = partGroupNames.map((name) => [name, new RegExp(partGroups[name].match)] as const)
  scene.traverse((object) => {
    if (object === scene) return
    const mesh = object as Mesh
    if (mesh.isMesh) {
      mesh.castShadow = object.name !== 'Sand'
      mesh.receiveShadow = true
    }
    if (object.name) parts[object.name] = object
    for (const [name, pattern] of patterns) {
      if (pattern.test(object.name)) groups[name].push(object)
    }
  })
  console.info('[reef-landing] model', JSON.stringify({
    nodes: Object.keys(parts).length,
    groups: Object.fromEntries(partGroupNames.map((name) => [name, groups[name].length])),
  }))
  return {
    root,
    scene,
    parts,
    groups,
    bounds,
    setMaterialParam(name, key, value) {
      const target = parts[name]
      if (!target) throw new Error(`Unknown part: ${name}`)
      target.traverse((object) => {
        const mesh = object as Mesh
        if (!mesh.isMesh) return
        for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
          const standard = material as MeshStandardMaterial
          const current = (standard as unknown as Record<string, unknown>)[key]
          if (current instanceof Color) current.set(value)
          else (standard as unknown as Record<string, unknown>)[key] = value
          standard.needsUpdate = true
        }
      })
    },
    dispose() {
      disposeObject(scene)
      root.clear()
    },
  }
}

export function disposeObject(object: Object3D) {
  const geometries = new Set<BufferGeometry>()
  const materials = new Set<Material>()
  const textures = new Set<Texture>()
  object.traverse((child) => {
    const mesh = child as Mesh
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
