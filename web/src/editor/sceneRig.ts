// scene.json → Three.js 場景的共用套用邏輯(editor Viewport 與 Embed 頁共用)。
// 座標與單位約定跟 Blender 端一致:spherical() 是 setup_lighting.spherical 的
// Z-up → Y-up 等價式;燈光瓦數以 Step 3-5 定量校正係數換算 three.js 強度。
import {
  Box3,
  Mesh,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  Vector3,
  type Object3D,
} from 'three'
import type { MaterialOverride, SceneJson } from './sceneStore'

// Blender 瓦數 → three.js DirectionalLight 強度(Key 400W ≈ 8.5,見 docs/render-consistency.md)
export const POWER_TO_INTENSITY = 8.5 / 400

// 模型在 viewer 端正規化為最長邊 1.6(Blender cleanup 端為 1.0,等比換算)
export const VIEWER_SCALE = 1.6

export function spherical(azimuthDeg: number, elevationDeg: number, distance: number): Vector3 {
  const az = (azimuthDeg * Math.PI) / 180
  const el = (elevationDeg * Math.PI) / 180
  return new Vector3(
    distance * Math.cos(el) * Math.sin(az),
    distance * Math.sin(el),
    distance * Math.cos(el) * Math.cos(az),
  )
}

export function focalToFov(focalMm: number): number {
  return (2 * Math.atan(18 / focalMm) * 180) / Math.PI // 36mm 感光片
}

/** 置中、最長邊 VIEWER_SCALE、底部 y=-0.8(與 ModelViewer 同約定)。回傳統計。 */
export function normalizeModel(model: Object3D): { triangles: number; centerY: number } {
  let triangles = 0
  model.traverse((o) => {
    const mesh = o as Mesh
    if (mesh.isMesh && mesh.geometry) {
      const g = mesh.geometry
      triangles += Math.floor((g.index ? g.index.count : g.attributes.position.count) / 3)
    }
  })
  const box = new Box3().setFromObject(model)
  const size = box.getSize(new Vector3())
  const center = box.getCenter(new Vector3())
  const scale = VIEWER_SCALE / Math.max(size.x, size.y, size.z)
  model.position.sub(center).multiplyScalar(scale)
  model.position.y += (size.y * scale) / 2 - 0.8
  model.scale.setScalar(scale)
  return { triangles, centerY: (size.y * scale) / 2 - 0.8 }
}

/** scene.lights → three.js 燈位置與強度。 */
export function lightRigs(scene: SceneJson) {
  return scene.lights.map((l) => ({
    id: l.id,
    pos: spherical(l.azimuth, l.elevation, 4),
    intensity: l.power * POWER_TO_INTENSITY,
  }))
}

/** scene.camera → 相機 FOV / 位置 / 目標(auto-frame,同 setup_camera.frame_camera)。 */
export function cameraRig(scene: SceneJson, centerY: number) {
  const fov = focalToFov(scene.camera.focal_mm)
  const dist = (VIEWER_SCALE / 2 / Math.tan(((fov / 2) * Math.PI) / 180)) * scene.camera.padding
  const target = new Vector3(0, centerY, 0)
  const position = spherical(scene.camera.azimuth, scene.camera.elevation, dist).add(target)
  return { fov, target, position }
}

export interface MaterialRig {
  names: string[]
  defaults: Record<string, { roughness: number; metallic: number }>
  /** 套用 materials_override(非破壞、可還原)+ wireframe 狀態。 */
  apply(overrides: Record<string, MaterialOverride>, wireframe?: boolean): void
}

/** 收集 GLB 材質並提供 override 套用(transmission/ior 以 lazy 升級 Physical 實現)。 */
export function createMaterialRig(model: Object3D): MaterialRig {
  interface Entry {
    mesh: Mesh
    original: MeshStandardMaterial
    r0: number
    m0: number
    physical?: MeshPhysicalMaterial
  }
  const entries = new Map<string, Entry[]>()
  model.traverse((o) => {
    const mesh = o as Mesh
    if (!mesh.isMesh) return
    const mat = mesh.material
    if (mat instanceof MeshStandardMaterial) {
      const list = entries.get(mat.name) ?? []
      list.push({ mesh, original: mat, r0: mat.roughness, m0: mat.metalness })
      entries.set(mat.name, list)
    }
  })

  return {
    names: [...entries.keys()],
    defaults: Object.fromEntries(
      [...entries].map(([name, [e]]) => [name, { roughness: e.r0, metallic: e.m0 }]),
    ),
    apply(overrides, wireframe = false) {
      for (const [name, list] of entries) {
        const ov = overrides[name] ?? {}
        const needPhysical = (ov.transmission ?? 0) > 0 || ov.ior !== undefined
        for (const e of list) {
          let mat: MeshStandardMaterial = e.original
          if (needPhysical) {
            // 注意要用 Standard 層級的 copy——Physical.copy 假設來源也是 Physical
            // (讀 clearcoatNormalScale 等欄位丟 TypeError);copy 會蓋掉 defines,
            // 必須補回 PHYSICAL,否則 fragment shader 編譯失敗、mesh 消失
            if (!e.physical) {
              e.physical = new MeshPhysicalMaterial()
              MeshStandardMaterial.prototype.copy.call(e.physical, e.original)
              e.physical.defines = { STANDARD: '', PHYSICAL: '' }
            }
            mat = e.physical
          }
          if (e.mesh.material !== mat) e.mesh.material = mat
          // glTF 慣例:factor 與貼圖相乘,tint 直接設 color 係數即可、貼圖不動
          mat.color.set(ov.base_color_tint ?? '#ffffff')
          mat.roughness = ov.roughness ?? e.r0
          mat.metalness = ov.metallic ?? e.m0
          mat.emissive.set(ov.emissive ?? '#000000')
          if (mat instanceof MeshPhysicalMaterial) {
            mat.transmission = ov.transmission ?? 0
            mat.ior = ov.ior ?? 1.45
          }
          mat.wireframe = wireframe
          mat.needsUpdate = true
        }
      }
    },
  }
}
