<script setup lang="ts">
// Phase 4B Editor 的中央 Viewport:同一 TresCanvas + OrbitControls + grid,
// 燈光 / 材質 / 相機 / 背景全部反應 sceneStore(即幀生效,GLB 不動)。
// scene.json → three.js 的套用邏輯在 ../editor/sceneRig.ts(與 Embed 頁共用)。
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'
import { computed, ref, watch, watchEffect } from 'vue'
import { ACESFilmicToneMapping, Vector3 } from 'three'
import { loadGlb } from './useGlb'
import SceneEnvironment from './SceneEnvironment.vue'
import { HDRI_INTENSITY, loadHdri } from './useHdri'
import { scene as sceneJson, editorUi } from '../editor/sceneStore'
import { cameraRig, createMaterialRig, lightRigs, normalizeModel } from '../editor/sceneRig'

const props = defineProps<{ wireframe?: boolean }>()

const [gltf, hdriTexture] = await Promise.all([
  loadGlb(sceneJson.model_url),
  loadHdri(),
])
const model = gltf.scene

const { triangles, centerY } = normalizeModel(model)
editorUi.stats.triangles = triangles
try {
  const res = await fetch(sceneJson.model_url, { method: 'HEAD' })
  const len = res.headers.get('content-length')
  editorUi.stats.bytes = len ? Number(len) : null
} catch {
  editorUi.stats.bytes = null
}

// --- 材質:收集名稱、套用 materials_override(非破壞性,可還原) ---
const materialRig = createMaterialRig(model)
editorUi.materialNames = materialRig.names
editorUi.activeMaterial = materialRig.names[0] ?? ''
editorUi.materialDefaults = materialRig.defaults
watchEffect(() => materialRig.apply(sceneJson.materials_override, !!props.wireframe))

// --- 燈光:store → 位置與強度 ---
const lights = computed(() => lightRigs(sceneJson))

// --- 相機:store(azimuth/elevation/focal/padding)→ 位置與 FOV ---
const controlsRef = ref<{ instance?: { object: any; target: any; update: () => void } } | null>(null)
const initCam = cameraRig(sceneJson, centerY)

function applyCamera() {
  const c = controlsRef.value?.instance
  if (!c) return
  const cam = c.object
  const rig = cameraRig(sceneJson, centerY)
  cam.position.copy(rig.position)
  cam.fov = rig.fov
  cam.updateProjectionMatrix()
  c.target.copy(rig.target)
  c.update()
}
watch(() => ({ ...sceneJson.camera }), applyCamera, { deep: true })
watch(controlsRef, () => applyCamera()) // controls 就緒時套用初始相機

// --- 背景:color / transparent / environment ---
const gridPos = new Vector3(0, -0.8, 0)
const bg = computed(() => sceneJson.environment.background)
const clearColor = computed(() => (bg.value.type === 'color' ? bg.value.value : '#1a1a2e'))
const sceneBackground = computed(() => {
  if (bg.value.type === 'color') return bg.value.value
  if (bg.value.type === 'environment') return 'environment'
  return undefined // transparent:MVP 顯示為深色 viewport 底
})

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
</script>

<template>
  <TresCanvas :clear-color="clearColor" :tone-mapping="ACESFilmicToneMapping" shadows>
    <TresPerspectiveCamera :position="initCam.position" :fov="initCam.fov" :look-at="initCam.target" />
    <OrbitControls ref="controlsRef" enable-damping :target="initCam.target" :min-distance="0.5" :max-distance="10" />
    <SceneEnvironment
      v-if="hdriTexture"
      :texture="hdriTexture"
      :intensity="sceneJson.environment.intensity ?? HDRI_INTENSITY"
      :rotation="sceneJson.environment.rotation ?? 0"
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
