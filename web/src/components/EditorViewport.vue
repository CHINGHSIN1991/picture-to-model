<script setup lang="ts">
// Phase 4B Editor 的中央 Viewport:同一 TresCanvas + OrbitControls + grid,
// 燈光 / 材質 / 相機 / 背景全部反應 sceneStore(即幀生效,GLB 不動)。
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'
import { computed, ref, watch, watchEffect } from 'vue'
import {
  ACESFilmicToneMapping,
  Box3,
  Mesh,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  Vector3,
} from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import SceneEnvironment from './SceneEnvironment.vue'
import { HDRI_INTENSITY, loadHdri } from './useHdri'
import { scene as sceneJson, editorUi } from '../editor/sceneStore'

const props = defineProps<{ wireframe?: boolean }>()

// Blender 瓦數 → three.js DirectionalLight 強度的換算係數。
// 由 Step 3-5 定量校正反推:Key 400W ≈ 8.5(docs/render-consistency.md)
const POWER_TO_INTENSITY = 8.5 / 400

const [gltf, hdriTexture] = await Promise.all([
  new GLTFLoader().loadAsync(sceneJson.model_url),
  loadHdri(),
])
const model = gltf.scene

// 統計 + 正規化(與 ModelViewer 相同約定:置中、最長邊 1.6、底部 y=-0.8)
let triangles = 0
model.traverse((o) => {
  const mesh = o as Mesh
  if (mesh.isMesh && mesh.geometry) {
    const g = mesh.geometry
    triangles += Math.floor((g.index ? g.index.count : g.attributes.position.count) / 3)
  }
})
editorUi.stats.triangles = triangles
try {
  const res = await fetch(sceneJson.model_url, { method: 'HEAD' })
  const len = res.headers.get('content-length')
  editorUi.stats.bytes = len ? Number(len) : null
} catch {
  editorUi.stats.bytes = null
}

const box = new Box3().setFromObject(model)
const size = box.getSize(new Vector3())
const center = box.getCenter(new Vector3())
const scale = 1.6 / Math.max(size.x, size.y, size.z)
model.position.sub(center).multiplyScalar(scale)
model.position.y += (size.y * scale) / 2 - 0.8
model.scale.setScalar(scale)
const centerY = (size.y * scale) / 2 - 0.8

// --- 材質:收集名稱、套用 materials_override(非破壞性,可還原) ---
interface Entry {
  mesh: Mesh
  original: MeshStandardMaterial
  r0: number // 原始 roughness / metalness(GLB 的 factor,還原用)
  m0: number
  physical?: MeshPhysicalMaterial // transmission > 0 時升級用,lazy 建立
}
const matEntries = new Map<string, Entry[]>()
model.traverse((o) => {
  const mesh = o as Mesh
  if (!mesh.isMesh) return
  const mat = mesh.material
  if (mat instanceof MeshStandardMaterial) {
    const list = matEntries.get(mat.name) ?? []
    list.push({ mesh, original: mat, r0: mat.roughness, m0: mat.metalness })
    matEntries.set(mat.name, list)
  }
})
editorUi.materialNames = [...matEntries.keys()]
editorUi.activeMaterial = editorUi.materialNames[0] ?? ''
editorUi.materialDefaults = Object.fromEntries(
  [...matEntries].map(([name, [e]]) => [name, { roughness: e.r0, metallic: e.m0 }]),
)

watchEffect(() => {
  for (const [name, entries] of matEntries) {
    const ov = sceneJson.materials_override[name] ?? {}
    const needPhysical = (ov.transmission ?? 0) > 0 || ov.ior !== undefined
    for (const e of entries) {
      let mat: MeshStandardMaterial = e.original
      if (needPhysical) {
        // MeshStandardMaterial 沒有 transmission/ior:lazy 升級成 Physical。
        // 注意要用 Standard 層級的 copy——Physical.copy 假設來源也是 Physical
        // (會讀 clearcoatNormalScale 等欄位而丟 TypeError)
        if (!e.physical) {
          e.physical = new MeshPhysicalMaterial()
          MeshStandardMaterial.prototype.copy.call(e.physical, e.original)
          // Standard 的 copy 會把 defines 一併蓋過來,弄丟 PHYSICAL define
          // → fragment shader 編譯失敗(mesh 直接消失),必須補回
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
      mat.wireframe = !!props.wireframe
      mat.needsUpdate = true
    }
  }
})

// --- 燈光:store → 位置與強度(座標轉換同 ModelViewer.spherical) ---
function spherical(azimuthDeg: number, elevationDeg: number, distance: number): Vector3 {
  const az = (azimuthDeg * Math.PI) / 180
  const el = (elevationDeg * Math.PI) / 180
  return new Vector3(
    distance * Math.cos(el) * Math.sin(az),
    distance * Math.sin(el),
    distance * Math.cos(el) * Math.cos(az),
  )
}
const lights = computed(() =>
  sceneJson.lights.map((l) => ({
    id: l.id,
    pos: spherical(l.azimuth, l.elevation, 4),
    intensity: l.power * POWER_TO_INTENSITY,
  })),
)

// --- 相機:store(azimuth/elevation/focal/padding)→ 位置與 FOV ---
const controlsRef = ref<{ instance?: { object: any; target: any; update: () => void } } | null>(null)
const cameraTarget = new Vector3(0, centerY, 0)

function focalToFov(focalMm: number): number {
  return (2 * Math.atan(18 / focalMm) * 180) / Math.PI // 36mm 感光片
}
function applyCamera() {
  const c = controlsRef.value?.instance
  if (!c) return
  const cam = c.object
  const fov = focalToFov(sceneJson.camera.focal_mm)
  const dist = (1.6 / 2 / Math.tan(((fov / 2) * Math.PI) / 180)) * sceneJson.camera.padding
  cam.position.copy(spherical(sceneJson.camera.azimuth, sceneJson.camera.elevation, dist).add(cameraTarget))
  cam.fov = fov
  cam.updateProjectionMatrix()
  c.target.copy(cameraTarget)
  c.update()
}
watch(() => ({ ...sceneJson.camera }), applyCamera, { deep: true })
watch(controlsRef, () => applyCamera()) // controls 就緒時套用初始相機

// 初始相機參數(controls 尚未就緒前由 template 提供)
const initFov = focalToFov(sceneJson.camera.focal_mm)
const initDist = (1.6 / 2 / Math.tan(((initFov / 2) * Math.PI) / 180)) * sceneJson.camera.padding
const initPos = spherical(sceneJson.camera.azimuth, sceneJson.camera.elevation, initDist).add(cameraTarget)

// --- Export GLB:把 materials_override 合成進 GLB(client 端,gltf-transform 屬 4B 後端) ---
async function exportGlb() {
  const { GLTFExporter } = await import('three/examples/jsm/exporters/GLTFExporter.js')
  const result = (await new GLTFExporter().parseAsync(model, { binary: true })) as ArrayBuffer
  const blob = new Blob([result], { type: 'model/gltf-binary' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'model_edited.glb'
  a.click()
  URL.revokeObjectURL(a.href)
}
defineExpose({ exportGlb })

// --- 背景:color / transparent / environment ---
const gridPos = new Vector3(0, -0.8, 0)
const bg = computed(() => sceneJson.environment.background)
const clearColor = computed(() => (bg.value.type === 'color' ? bg.value.value : '#1a1a2e'))
const sceneBackground = computed(() => {
  if (bg.value.type === 'color') return bg.value.value
  if (bg.value.type === 'environment') return 'environment'
  return undefined // transparent:MVP 顯示為深色 viewport 底
})
</script>

<template>
  <TresCanvas :clear-color="clearColor" :tone-mapping="ACESFilmicToneMapping" shadows>
    <TresPerspectiveCamera :position="initPos" :fov="initFov" :look-at="cameraTarget" />
    <OrbitControls ref="controlsRef" enable-damping :target="cameraTarget" :min-distance="0.5" :max-distance="10" />
    <SceneEnvironment
      v-if="hdriTexture"
      :texture="hdriTexture"
      :intensity="sceneJson.environment.intensity ?? HDRI_INTENSITY"
      :background="sceneBackground === 'environment' ? undefined : sceneBackground"
      :env-as-background="sceneBackground === 'environment'"
    />
    <TresDirectionalLight
      v-for="l in lights"
      :key="l.id"
      :position="l.pos"
      :intensity="l.intensity"
    />
    <primitive :object="model" />
    <TresGridHelper v-if="bg.type === 'transparent'" :args="[10, 20, '#334', '#223']" :position="gridPos" />
  </TresCanvas>
</template>
