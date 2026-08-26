<script setup lang="ts">
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'
import { ref, watch } from 'vue'
import {
  ACESFilmicToneMapping,
  Box3,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Vector3,
  type Material,
} from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js'
import type { CameraSync } from './cameraSync'
import SceneEnvironment from './SceneEnvironment.vue'

const props = defineProps<{
  url: string
  // 比較模式:傳入共享相機狀態與 pane 代號,雙邊視角同步
  sync?: CameraSync
  paneId?: string
  // 結構線模式:拿掉材質、顯示三角形線框
  wireframe?: boolean
  // 攝影棚模式(一致性驗證用):白底、相機與打光對齊 Blender 端
  // setup_camera / setup_lighting 的球座標配置
  studio?: boolean
}>()
const emit = defineEmits<{ loaded: [stats: { triangles: number; bytes: number | null }] }>()

// 與 Blender 相同的 HDRI(setup_lighting.py 的 DEFAULT_HDRI,強度 0.4)
const HDRI_URL = '/hdri/studio_small_08_1k.hdr'
const HDRI_INTENSITY = 0.4

const [gltf, hdriTexture] = await Promise.all([
  new GLTFLoader().loadAsync(props.url),
  new RGBELoader().loadAsync(HDRI_URL),
])
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

// AI 生成模型的原點與尺度不可預期:置中並縮放到單位大小
const box = new Box3().setFromObject(model)
const size = box.getSize(new Vector3())
const center = box.getCenter(new Vector3())
const scale = 1.6 / Math.max(size.x, size.y, size.z)
model.position.sub(center).multiplyScalar(scale)
model.position.y += (size.y * scale) / 2 - 0.8
model.scale.setScalar(scale)
const centerY = (size.y * scale) / 2 - 0.8 // 正規化後的模型中心高度

// 球座標 → three.js(Y-up)。與 Blender 端 setup_lighting.spherical(Z-up,
// 方位角 0° = 正前方)經 glTF 座標轉換(x,y,z) → (x,z,−y) 後等價。
function spherical(azimuthDeg: number, elevationDeg: number, distance: number): Vector3 {
  const az = (azimuthDeg * Math.PI) / 180
  const el = (elevationDeg * Math.PI) / 180
  return new Vector3(
    distance * Math.cos(el) * Math.sin(az),
    distance * Math.sin(el),
    distance * Math.cos(el) * Math.cos(az),
  )
}

// --- 攝影棚模式:對齊 render.py 的取景與打光 ---
// 相機:方位角 30° / 仰角 18° / 50mm(36mm 感光片 → FOV ≈ 39.6°),
// 距離 = (最長邊/2) / tan(FOV/2) × 留白 1.4(同 setup_camera.frame_camera)
const STUDIO_FOV = 39.6
const STUDIO_DIST = (1.6 / 2 / Math.tan(((STUDIO_FOV / 2) * Math.PI) / 180)) * 1.4

const cameraTarget = props.studio ? new Vector3(0, centerY, 0) : new Vector3(0, 0, 0)
const cameraPos = props.studio
  ? spherical(30, 18, STUDIO_DIST).add(cameraTarget)
  : new Vector3(2.2, 1.4, 2.2)
const cameraFov = props.studio ? STUDIO_FOV : 45

// 三點打光角度同 setup_lighting.py(Key 75°/45°、Fill −30°/20°、Rim 200°/40°);
// 強度按 Blender 瓦數比例 400:130:250,整體係數目視校正
const studioLights = [
  { pos: spherical(75, 45, 4), intensity: 8.5 },
  { pos: spherical(-30, 20, 4), intensity: 2.7 },
  { pos: spherical(200, 40, 4), intensity: 5.2 },
]

const keyLightPos = new Vector3(4, 6, 4)
const fillLightPos = new Vector3(-4, 2, -4)
const gridPos = new Vector3(0, -0.8, 0)

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
  <TresCanvas
    :clear-color="studio ? '#ffffff' : '#1a1a2e'"
    :tone-mapping="ACESFilmicToneMapping"
    shadows
  >
    <TresPerspectiveCamera :position="cameraPos" :fov="cameraFov" :look-at="cameraTarget" />
    <OrbitControls
      ref="controlsRef"
      enable-damping
      :target="cameraTarget"
      :min-distance="1"
      :max-distance="8"
      @change="onControlsChange"
    />
    <!-- 與 Blender 同一張 HDRI 作 IBL:取代環境光,反射與整體照明一致 -->
    <SceneEnvironment
      :texture="hdriTexture"
      :intensity="HDRI_INTENSITY"
      :background="studio ? '#ffffff' : undefined"
    />
    <template v-if="studio">
      <TresDirectionalLight
        v-for="(l, i) in studioLights"
        :key="i"
        :position="l.pos"
        :intensity="l.intensity"
      />
    </template>
    <template v-else>
      <TresDirectionalLight :position="keyLightPos" :intensity="1.4" cast-shadow />
      <TresDirectionalLight :position="fillLightPos" :intensity="0.4" />
    </template>
    <primitive :object="model" />
    <TresGridHelper v-if="!studio" :args="[10, 20, '#334', '#223']" :position="gridPos" />
  </TresCanvas>
</template>
