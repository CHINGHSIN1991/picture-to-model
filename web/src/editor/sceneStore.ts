// Phase 4B Scene Editor 的單一真相來源(對映 docs/scene-schema.md v0)。
// MVP 先用模組層 reactive(零相依);4A 整合多專案時再換 Pinia。
// 持久化:debounce 寫 localStorage(之後換 scenes 表 JSONB)。
import { reactive, watch } from 'vue'

export interface SceneLight {
  id: 'key' | 'fill' | 'rim'
  type: 'area'
  azimuth: number
  elevation: number
  power: number // Blender 瓦數(schema 單位);viewer 端換算 three.js 強度
}

export interface MaterialOverride {
  base_color_tint?: string
  roughness?: number
  metallic?: number
  emissive?: string
  transmission?: number
  ior?: number
}

export interface SceneJson {
  version: 0
  model_url: string
  environment: {
    hdri: string
    intensity: number
    background: { type: 'color' | 'transparent' | 'environment'; value: string }
  }
  lights: SceneLight[]
  camera: { azimuth: number; elevation: number; focal_mm: number; padding: number }
  materials_override: Record<string, MaterialOverride>
  render: {
    engine: 'cycles'
    samples: number
    resolution: number
    tone_mapping: 'agx'
    transparent: boolean
  }
}

// 預設值 = 現有 pipeline 參數(setup_lighting / setup_camera / render.py 現值)
export function defaultScene(modelUrl = '/models/model.glb'): SceneJson {
  return {
    version: 0,
    model_url: modelUrl,
    environment: {
      hdri: 'studio_small_08_1k',
      intensity: 0.4,
      background: { type: 'color', value: '#FFFFFF' },
    },
    lights: [
      { id: 'key', type: 'area', azimuth: 75, elevation: 45, power: 400 },
      { id: 'fill', type: 'area', azimuth: -30, elevation: 20, power: 130 },
      { id: 'rim', type: 'area', azimuth: 200, elevation: 40, power: 250 },
    ],
    camera: { azimuth: 30, elevation: 18, focal_mm: 50, padding: 1.4 },
    materials_override: {},
    render: { engine: 'cycles', samples: 128, resolution: 1600, tone_mapping: 'agx', transparent: true },
  }
}

const STORAGE_KEY = 'p2m-scene-v0'

function load(): SceneJson | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (parsed?.version !== 0) return null
    // 未知欄位保留、缺欄位補預設(schema 的向前相容原則)
    return { ...defaultScene(), ...parsed }
  } catch {
    return null
  }
}

export const scene = reactive<SceneJson>(load() ?? defaultScene())

// 編輯器 UI 狀態(不進 scene.json)
export const editorUi = reactive({
  selection: 'model' as 'model' | 'key' | 'fill' | 'rim' | 'hdri' | 'camera',
  tab: 'material' as 'material' | 'light' | 'camera' | 'bg',
  materialNames: [] as string[], // viewport 載入 GLB 後回填
  materialDefaults: {} as Record<string, { roughness: number; metallic: number }>, // GLB 原始 factor(滑桿未 override 時的顯示值)
  activeMaterial: '',
  saved: true,
  stats: { triangles: 0, bytes: null as number | null },
})

let saveTimer: ReturnType<typeof setTimeout> | undefined
watch(
  scene,
  () => {
    editorUi.saved = false
    clearTimeout(saveTimer)
    saveTimer = setTimeout(() => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(scene))
      editorUi.saved = true
    }, 300)
  },
  { deep: true },
)

export function resetScene(modelUrl?: string) {
  Object.assign(scene, defaultScene(modelUrl ?? scene.model_url))
  scene.materials_override = {}
}

export function overrideFor(name: string): MaterialOverride {
  return (scene.materials_override[name] ??= {})
}

export function downloadSceneJson() {
  const blob = new Blob([JSON.stringify(scene, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'scene.json'
  a.click()
  URL.revokeObjectURL(a.href)
}
