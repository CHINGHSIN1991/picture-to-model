<script setup lang="ts">
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'
import { computed, ref, watch } from 'vue'
import {
  Box3,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Vector3,
  type Material,
} from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import type { CameraSync } from './cameraSync'

const props = defineProps<{
  url: string
  // 比較模式:傳入共享相機狀態與 pane 代號,雙邊視角同步
  sync?: CameraSync
  paneId?: string
  // 結構線模式:拿掉材質、顯示三角形線框
  wireframe?: boolean
}>()
const emit = defineEmits<{ loaded: [stats: { triangles: number; bytes: number | null }] }>()

const gltf = await new GLTFLoader().loadAsync(props.url)
const model = gltf.scene

// 統計三角形數與檔案大小,給比較頁顯示
let triangles = 0
model.traverse((o) => {
  const mesh = o as Mesh
  if (mesh.isMesh && mesh.geometry) {
    const g = mesh.geometry
    triangles += Math.floor((g.index ? g.index.count : g.attributes.position.count) / 3)
  }
})
let bytes: number | null = null
try {
  const res = await fetch(props.url, { method: 'HEAD' })
  const len = res.headers.get('content-length')
  bytes = len ? Number(len) : null
} catch {
  // 拿不到檔案大小就不顯示
}
emit('loaded', { triangles, bytes })

const cameraPos = new Vector3(2.2, 1.4, 2.2)
const origin = new Vector3(0, 0, 0)
const keyLightPos = new Vector3(4, 6, 4)
const fillLightPos = new Vector3(-4, 2, -4)
const gridPos = new Vector3(0, -0.8, 0)

// AI 生成模型的原點與尺度不可預期:置中並縮放到單位大小
const normalized = computed(() => {
  const box = new Box3().setFromObject(model)
  const size = box.getSize(new Vector3())
  const center = box.getCenter(new Vector3())
  const scale = 1.6 / Math.max(size.x, size.y, size.z)
  model.position.sub(center).multiplyScalar(scale)
  model.position.y += (size.y * scale) / 2 - 0.8
  model.scale.setScalar(scale)
  return model
})

// --- 結構線模式:素色底 + 三角形線框疊加(共用 geometry,不複製記憶體) ---
const baseMat = new MeshStandardMaterial({
  color: 0x9aa3b2,
  roughness: 0.9,
  polygonOffset: true, // 底面稍微後退,避免與線框 z-fighting
  polygonOffsetFactor: 1,
  polygonOffsetUnits: 1,
})
const wireMat = new MeshBasicMaterial({ color: 0x4fd1c5, wireframe: true })
const originalMats = new Map<Mesh, Material | Material[]>()
const overlays: Mesh[] = []

function setWireframe(on: boolean) {
  if (on && originalMats.size === 0) {
    const meshes: Mesh[] = []
    model.traverse((o) => {
      if ((o as Mesh).isMesh && !o.userData.wireOverlay) meshes.push(o as Mesh)
    })
    for (const mesh of meshes) {
      originalMats.set(mesh, mesh.material)
      mesh.material = baseMat
      const overlay = new Mesh(mesh.geometry, wireMat)
      overlay.userData.wireOverlay = true
      mesh.add(overlay)
      overlays.push(overlay)
    }
  } else if (!on && originalMats.size > 0) {
    for (const [mesh, mat] of originalMats) mesh.material = mat
    for (const overlay of overlays) overlay.removeFromParent()
    originalMats.clear()
    overlays.length = 0
  }
}
watch(() => props.wireframe, (on) => setWireframe(!!on), { immediate: true })

// --- 相機同步(僅比較模式) ---
const controlsRef = ref<{ instance?: { object: any; target: any; update: () => void } } | null>(null)

function onControlsChange() {
  const c = controlsRef.value?.instance
  if (!props.sync || !props.paneId || !c) return
  if (props.sync.active !== props.paneId) return // 只有滑鼠所在的 pane 發布
  props.sync.pos = [c.object.position.x, c.object.position.y, c.object.position.z]
  props.sync.target = [c.target.x, c.target.y, c.target.z]
}

watch(
  () => (props.sync ? [...props.sync.pos, ...props.sync.target].join(',') : ''),
  () => {
    const c = controlsRef.value?.instance
    if (!props.sync || !c || props.sync.active === props.paneId) return
    c.object.position.set(...props.sync.pos)
    c.target.set(...props.sync.target)
    c.update()
  },
)
</script>

<template>
  <TresCanvas clear-color="#1a1a2e" shadows>
    <TresPerspectiveCamera :position="cameraPos" :look-at="origin" />
    <OrbitControls
      ref="controlsRef"
      enable-damping
      :min-distance="1"
      :max-distance="8"
      @change="onControlsChange"
    />
    <TresAmbientLight :intensity="0.5" />
    <TresDirectionalLight :position="keyLightPos" :intensity="1.4" cast-shadow />
    <TresDirectionalLight :position="fillLightPos" :intensity="0.4" />
    <primitive :object="normalized" />
    <TresGridHelper :args="[10, 20, '#334', '#223']" :position="gridPos" />
  </TresCanvas>
</template>
