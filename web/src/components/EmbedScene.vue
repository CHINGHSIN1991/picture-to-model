<script setup lang="ts">
// Embed 的 3D 場景(async):載入 GLB + HDRI(+ 可選 scene.json)並套用。
// 與 editor 共用 sceneRig 的套用邏輯——同一份 scene.json、同一個渲染結果。
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'
import { ACESFilmicToneMapping } from 'three'
import { loadGlb } from './useGlb'
import SceneEnvironment from './SceneEnvironment.vue'
import { HDRI_URL, HDRI_URL_EMBED, loadHdri } from './useHdri'
import { defaultScene, mergeScene, type SceneJson } from '../editor/sceneStore'
import { cameraRig, createMaterialRig, lightRigs, normalizeModel } from '../editor/sceneRig'

const props = defineProps<{
  modelUrl: string
  sceneUrl?: string
}>()
const emit = defineEmits<{ loaded: [] }>()

// scene.json 可選:沒有就用 pipeline 預設(等同未編輯過的攝影棚)
async function fetchScene(): Promise<SceneJson> {
  if (!props.sceneUrl) return defaultScene(props.modelUrl)
  const res = await fetch(props.sceneUrl)
  if (!res.ok) throw new Error(`scene.json 載入失敗: ${res.status}`)
  return mergeScene(await res.json())
}

// HDRI 解析度依 scene 決定:只做 IBL 時用 512 降檔版(388KB),
// 背景 type=environment(HDRI 上畫面)才需要 1k;與 GLB 載入並行。
const scenePromise = fetchScene()
const hdriPromise = scenePromise.then((s) =>
  loadHdri(s.environment.background.type === 'environment' ? HDRI_URL : HDRI_URL_EMBED),
)
const [gltf, hdriTexture, scene] = await Promise.all([
  loadGlb(props.modelUrl),
  hdriPromise,
  scenePromise,
])
const model = gltf.scene

const { centerY } = normalizeModel(model)
createMaterialRig(model).apply(scene.materials_override)
const lights = lightRigs(scene)
const cam = cameraRig(scene, centerY)

const bg = scene.environment.background
const clearColor = bg.type === 'color' ? bg.value : '#ffffff' // 嵌入頁 transparent 也給白底
const envAsBackground = bg.type === 'environment'

emit('loaded')
</script>

<template>
  <TresCanvas :clear-color="clearColor" :tone-mapping="ACESFilmicToneMapping">
    <TresPerspectiveCamera :position="cam.position" :fov="cam.fov" :look-at="cam.target" />
    <OrbitControls enable-damping :target="cam.target" :min-distance="0.5" :max-distance="10" />
    <SceneEnvironment
      v-if="hdriTexture"
      :texture="hdriTexture"
      :intensity="scene.environment.intensity"
      :rotation="scene.environment.rotation ?? 0"
      :background="envAsBackground ? undefined : clearColor"
      :env-as-background="envAsBackground"
    />
    <TresDirectionalLight
      v-for="l in lights"
      :key="l.id"
      :position="l.pos"
      :intensity="l.intensity"
    />
    <primitive :object="model" />
  </TresCanvas>
</template>
