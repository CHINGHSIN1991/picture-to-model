<script setup lang="ts">
// Phase 4B Scene Editor(前端 MVP):三欄 Figma 式,滑桿全數對映 Scene Schema。
// 值只寫入 scene.json(localStorage),GLB 不動;Render / Embed 的後端屬 4A/4B 後續。
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import EditorViewport from './EditorViewport.vue'
import { MODELS } from '../modelList'
import {
  scene,
  editorUi,
  history,
  mergeScene,
  overrideFor,
  resetScene,
  downloadSceneJson,
  undo,
  redo,
  type SceneLight,
} from '../editor/sceneStore'

const viewportRef = ref<InstanceType<typeof EditorViewport> | null>(null)
const wireframe = ref(false)
const toast = ref('')
let toastTimer: ReturnType<typeof setTimeout> | undefined
function showToast(msg: string) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 2600)
}

const modelName = computed(() => scene.model_url.split('/').pop()?.replace('.glb', '') ?? '')

// --- Undo / Redo:⌘/Ctrl+Z、Shift+⌘/Ctrl+Z ---
const canUndo = computed(() => history.index > 0)
const canRedo = computed(() => history.index < history.stack.length - 1)
function onKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z') {
    e.preventDefault()
    e.shiftKey ? redo() : undo()
  }
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

// --- Scene 樹選取 → Inspector tab ---
function select(sel: typeof editorUi.selection) {
  editorUi.selection = sel
  editorUi.tab = sel === 'model' ? 'material' : sel === 'camera' ? 'camera' : 'light'
}

// --- Material tab:滑桿讀寫 materials_override(非破壞性) ---
const activeOverride = computed(() => scene.materials_override[editorUi.activeMaterial] ?? {})
const matDefault = computed(() => editorUi.materialDefaults[editorUi.activeMaterial] ?? { roughness: 0.5, metallic: 0 })
function setMat<K extends 'roughness' | 'metallic' | 'transmission' | 'ior'>(field: K, v: string) {
  overrideFor(editorUi.activeMaterial)[field] = Number(v)
}
function setMatColor(field: 'base_color_tint' | 'emissive', v: string) {
  overrideFor(editorUi.activeMaterial)[field] = v
}
function resetMaterial() {
  delete scene.materials_override[editorUi.activeMaterial]
}

// --- Light tab ---
const selectedLight = computed<SceneLight>(
  () => scene.lights.find((l) => l.id === editorUi.selection) ?? scene.lights[0],
)

// --- Camera tab presets(mockup:Front · Side · Iso) ---
const presets = [
  { label: 'Front', azimuth: 0, elevation: 5 },
  { label: 'Side', azimuth: 90, elevation: 5 },
  { label: 'Iso', azimuth: 45, elevation: 30 },
]
function applyPreset(p: (typeof presets)[number]) {
  scene.camera.azimuth = p.azimuth
  scene.camera.elevation = p.elevation
}

// --- 頂欄動作 ---
async function copyText(text: string, okMsg: string) {
  try {
    await navigator.clipboard.writeText(text)
    showToast(okMsg)
  } catch {
    console.info(text) // clipboard 被拒(權限 / 非安全環境)時輸出到 console
    showToast('無法寫入剪貼簿,內容已輸出到 console')
  }
}

function copyRenderCmd() {
  // poster 渲染(配角):CLI 已可完整消費 scene.json,產出 poster.webp 不覆蓋官方 preview
  const cmd = `uv run scripts/render_model.py output/<job_id> --scene-json <下載的 scene.json 路徑>`
  copyText(cmd, '已複製 poster 渲染 CLI:下載 scene.json 後帶入 --scene-json(產出 poster.webp)')
}

// 🎯 Embed(主產出):GLB / hdri / scene.json / poster 全為靜態檔,靜態託管即可嵌
function copyEmbedCode() {
  const src = `${location.origin}/?mode=embed&model=${encodeURIComponent(scene.model_url)}&scene=<scene.json 的 URL>&poster=<poster.webp 的 URL>`
  const code = `<iframe src="${src}" width="800" height="600" style="border:0" loading="lazy" title="3D model"></iframe>`
  copyText(code, '已複製 iframe 嵌入碼——把 GLB / hdri / scene.json / poster 放上靜態託管後替換 URL')
}

// 匯入 scene.json(跨機器 / 跨 job 帶回編輯;經 mergeScene 補預設欄位)
const importInput = ref<HTMLInputElement | null>(null)
async function onImportScene(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    Object.assign(scene, mergeScene(JSON.parse(await file.text())))
    showToast(`已匯入 ${file.name}`)
  } catch (err) {
    showToast(`匯入失敗:${err instanceof Error ? err.message : err}`)
  }
  ;(e.target as HTMLInputElement).value = ''
}
async function exportGlb() {
  await viewportRef.value?.exportGlb()
  showToast('已匯出 model_edited.glb(材質 override 已合成)')
}
function onReset() {
  resetScene()
  showToast('已重設為 pipeline 預設值')
}
function switchModel(url: string) {
  scene.model_url = url
  scene.materials_override = {} // 材質名稱是 per-GLB 的,換模型即失效
}
</script>

<template>
  <div class="editor">
    <!-- 頂欄 -->
    <header class="topbar">
      <span class="project">◆ picture-to-model — {{ modelName }} Scene</span>
      <nav class="undo-redo">
        <button :disabled="!canUndo" title="復原(⌘Z)" @click="undo()">↶</button>
        <button :disabled="!canRedo" title="重做(⇧⌘Z)" @click="redo()">↷</button>
      </nav>
      <span v-if="toast" class="toast">{{ toast }}</span>
      <div class="actions">
        <button @click="copyRenderCmd">Render poster</button>
        <button @click="exportGlb">Export GLB</button>
        <button @click="downloadSceneJson">scene.json ↓</button>
        <button @click="importInput?.click()">scene.json ↑</button>
        <input ref="importInput" type="file" accept="application/json,.json" hidden @change="onImportScene" />
        <button title="複製 iframe 嵌入碼(靜態託管即可嵌,4A 之後補 public URL 產生器)" @click="copyEmbedCode">Embed</button>
      </div>
    </header>

    <div class="columns">
      <!-- 左欄:Scene 樹 -->
      <aside class="tree">
        <h2>Scene</h2>
        <button class="node" :class="{ active: editorUi.selection === 'model' }" @click="select('model')">
          <strong>{{ modelName }}.glb</strong>
          <small>{{ editorUi.stats.triangles.toLocaleString('en-US') }} tris</small>
        </button>
        <select class="model-switch" :value="scene.model_url" @change="switchModel(($event.target as HTMLSelectElement).value)">
          <option v-for="m in MODELS" :key="m" :value="m">{{ m.split('/').pop() }}</option>
        </select>
        <button
          v-for="l in scene.lights"
          :key="l.id"
          class="node"
          :class="{ active: editorUi.selection === l.id }"
          @click="select(l.id)"
        >
          <strong>{{ { key: 'Key Light', fill: 'Fill Light', rim: 'Rim Light' }[l.id] }}</strong>
          <small>area {{ l.power }}W</small>
        </button>
        <button class="node" :class="{ active: editorUi.selection === 'hdri' }" @click="select('hdri')">
          <strong>HDRI</strong>
          <small>studio · {{ scene.environment.intensity }}</small>
        </button>
        <button class="node" :class="{ active: editorUi.selection === 'camera' }" @click="select('camera')">
          <strong>Camera</strong>
          <small>{{ scene.camera.azimuth }}°/{{ scene.camera.elevation }}° {{ scene.camera.focal_mm }}mm</small>
        </button>
        <button class="reset" @click="onReset">重設 Scene</button>
      </aside>

      <!-- 中央:Viewport -->
      <main class="viewport">
        <div class="statusbar">
          {{ editorUi.stats.triangles.toLocaleString('en-US') }} tris
          <template v-if="editorUi.stats.bytes != null"> · {{ (editorUi.stats.bytes / 1024 / 1024).toFixed(1) }}MB</template>
          · Scene {{ editorUi.saved ? '已儲存' : '儲存中…' }}
        </div>
        <div class="canvas-host">
          <Suspense :key="scene.model_url">
            <EditorViewport ref="viewportRef" :wireframe="wireframe" />
            <template #fallback><p class="loading">載入模型中…</p></template>
          </Suspense>
        </div>
        <div class="viewport-tools">
          <span class="hint">Orbit / Pan / Zoom</span>
          <span>
            <button v-for="p in presets" :key="p.label" @click="applyPreset(p)">{{ p.label }}</button>
          </span>
          <label><input v-model="wireframe" type="checkbox" /> Wireframe</label>
        </div>
      </main>

      <!-- 右欄:Inspector -->
      <aside class="inspector">
        <nav class="tabs">
          <button
            v-for="t in ['material', 'light', 'camera', 'bg'] as const"
            :key="t"
            :class="{ active: editorUi.tab === t }"
            @click="editorUi.tab = t"
          >
            {{ { material: 'Material', light: 'Light', camera: 'Camera', bg: 'BG' }[t] }}
          </button>
        </nav>

        <!-- Material -->
        <div v-if="editorUi.tab === 'material'" class="panel">
          <label class="row">
            <span>材質</span>
            <select v-model="editorUi.activeMaterial">
              <option v-for="m in editorUi.materialNames" :key="m" :value="m">{{ m || '(未命名)' }}</option>
            </select>
          </label>
          <label class="row">
            <span>Base Color</span>
            <input type="color" :value="activeOverride.base_color_tint ?? '#ffffff'" @input="setMatColor('base_color_tint', ($event.target as HTMLInputElement).value)" />
          </label>
          <label class="row slider">
            <span>Roughness</span>
            <input type="range" min="0" max="1" step="0.01" :value="activeOverride.roughness ?? matDefault.roughness" @input="setMat('roughness', ($event.target as HTMLInputElement).value)" />
            <code>{{ (activeOverride.roughness ?? matDefault.roughness).toFixed(2) }}</code>
          </label>
          <label class="row slider">
            <span>Metallic</span>
            <input type="range" min="0" max="1" step="0.01" :value="activeOverride.metallic ?? matDefault.metallic" @input="setMat('metallic', ($event.target as HTMLInputElement).value)" />
            <code>{{ (activeOverride.metallic ?? matDefault.metallic).toFixed(2) }}</code>
          </label>
          <label class="row slider">
            <span>Transmission</span>
            <input type="range" min="0" max="1" step="0.01" :value="activeOverride.transmission ?? 0" @input="setMat('transmission', ($event.target as HTMLInputElement).value)" />
            <code>{{ (activeOverride.transmission ?? 0).toFixed(2) }}</code>
          </label>
          <label class="row slider">
            <span>IOR</span>
            <input type="range" min="1" max="2.5" step="0.01" :value="activeOverride.ior ?? 1.45" @input="setMat('ior', ($event.target as HTMLInputElement).value)" />
            <code>{{ (activeOverride.ior ?? 1.45).toFixed(2) }}</code>
          </label>
          <label class="row">
            <span>Emissive</span>
            <input type="color" :value="activeOverride.emissive ?? '#000000'" @input="setMatColor('emissive', ($event.target as HTMLInputElement).value)" />
          </label>
          <button class="minor" @click="resetMaterial">還原此材質</button>
          <p class="note">值只寫入 Scene JSON,GLB 不動;transmission = fishbowl 玻璃解法</p>
        </div>

        <!-- Light -->
        <div v-else-if="editorUi.tab === 'light'" class="panel">
          <label class="row">
            <span>光源</span>
            <select :value="selectedLight.id" @change="editorUi.selection = ($event.target as HTMLSelectElement).value as any">
              <option v-for="l in scene.lights" :key="l.id" :value="l.id">{{ l.id }}</option>
            </select>
          </label>
          <label class="row slider">
            <span>Azimuth</span>
            <input v-model.number="selectedLight.azimuth" type="range" min="-180" max="360" step="1" />
            <code>{{ selectedLight.azimuth }}°</code>
          </label>
          <label class="row slider">
            <span>Elevation</span>
            <input v-model.number="selectedLight.elevation" type="range" min="0" max="90" step="1" />
            <code>{{ selectedLight.elevation }}°</code>
          </label>
          <label class="row slider">
            <span>Power</span>
            <input v-model.number="selectedLight.power" type="range" min="0" max="1000" step="5" />
            <code>{{ selectedLight.power }}W</code>
          </label>
          <label class="row slider">
            <span>HDRI 強度</span>
            <input v-model.number="scene.environment.intensity" type="range" min="0" max="2" step="0.05" />
            <code>{{ scene.environment.intensity.toFixed(2) }}</code>
          </label>
          <label class="row slider">
            <span>HDRI 旋轉</span>
            <input v-model.number="scene.environment.rotation" type="range" min="0" max="360" step="1" />
            <code>{{ scene.environment.rotation }}°</code>
          </label>
        </div>

        <!-- Camera -->
        <div v-else-if="editorUi.tab === 'camera'" class="panel">
          <div class="row">
            <span>Preset</span>
            <span><button v-for="p in presets" :key="p.label" class="minor" @click="applyPreset(p)">{{ p.label }}</button></span>
          </div>
          <label class="row slider">
            <span>Azimuth</span>
            <input v-model.number="scene.camera.azimuth" type="range" min="-180" max="360" step="1" />
            <code>{{ scene.camera.azimuth }}°</code>
          </label>
          <label class="row slider">
            <span>Elevation</span>
            <input v-model.number="scene.camera.elevation" type="range" min="0" max="89" step="1" />
            <code>{{ scene.camera.elevation }}°</code>
          </label>
          <label class="row slider">
            <span>焦距</span>
            <input v-model.number="scene.camera.focal_mm" type="range" min="24" max="135" step="1" />
            <code>{{ scene.camera.focal_mm }}mm</code>
          </label>
          <label class="row slider">
            <span>留白</span>
            <input v-model.number="scene.camera.padding" type="range" min="1" max="2" step="0.05" />
            <code>{{ scene.camera.padding.toFixed(2) }}</code>
          </label>
          <p class="note">auto-frame:距離依 bounding box 與 FOV 計算(= setup_camera.py)</p>
        </div>

        <!-- BG -->
        <div v-else class="panel">
          <label v-for="t in ['color', 'transparent', 'environment'] as const" :key="t" class="row radio">
            <input v-model="scene.environment.background.type" type="radio" :value="t" />
            <span>{{ { color: '純色', transparent: '透明(渲染用)', environment: 'HDRI 環境' }[t] }}</span>
          </label>
          <label v-if="scene.environment.background.type === 'color'" class="row">
            <span>顏色</span>
            <input v-model="scene.environment.background.value" type="color" />
          </label>
          <p class="note">透明背景對映 render.py 的 film_transparent(合成白底商品圖)</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  font-size: 0.85rem;
}
.topbar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.45rem 0.9rem;
  background: #101024;
  border-bottom: 1px solid #26263a;
}
.project {
  font-family: ui-monospace, monospace;
  font-weight: 600;
}
.toast {
  color: #7ee0a3;
  font-size: 0.8rem;
}
.undo-redo {
  display: flex;
  gap: 0.25rem;
}
.undo-redo button {
  background: #1f1f36;
  color: #ccc;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 0.2rem 0.55rem;
  font-size: 0.95rem;
  cursor: pointer;
}
.undo-redo button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.actions {
  margin-left: auto;
  display: flex;
  gap: 0.5rem;
}
.actions button {
  background: #2c4a63;
  color: #dfe9f3;
  border: none;
  border-radius: 6px;
  padding: 0.35rem 0.9rem;
  cursor: pointer;
}
.actions button:last-child {
  background: #2ea28d;
  color: #06251f;
}
.actions button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.columns {
  flex: 1;
  display: grid;
  grid-template-columns: 220px 1fr 300px;
  min-height: 0;
}
.tree,
.inspector {
  background: #16162a;
  padding: 0.75rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.tree h2 {
  font-size: 0.7rem;
  letter-spacing: 0.15em;
  color: #7a7a9a;
  margin: 0 0 0.25rem;
}
.node {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.1rem;
  background: transparent;
  border: none;
  border-radius: 8px;
  padding: 0.45rem 0.6rem;
  color: #cfcfe6;
  cursor: pointer;
  text-align: left;
}
.node small {
  color: #7a7a9a;
}
.node.active {
  background: #3a5a78;
  color: #fff;
}
.node.active small {
  color: #b8d0e6;
}
.model-switch,
.panel select {
  background: #26263a;
  color: #eee;
  border: 1px solid #444;
  border-radius: 6px;
  padding: 0.25rem 0.4rem;
  max-width: 100%;
}
.reset {
  margin-top: auto;
  background: none;
  border: 1px solid #444;
  border-radius: 6px;
  color: #9a9ab8;
  padding: 0.3rem;
  cursor: pointer;
}
.viewport {
  position: relative;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #0d0d18;
  border-left: 1px solid #26263a;
  border-right: 1px solid #26263a;
}
.statusbar {
  padding: 0.3rem 0.75rem;
  font-family: ui-monospace, monospace;
  font-size: 0.75rem;
  color: #8fa3b8;
  background: #101024;
}
.canvas-host {
  flex: 1;
  min-height: 0;
  position: relative;
  overflow: hidden;
}
.loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #888;
}
.viewport-tools {
  display: flex;
  align-items: center;
  gap: 1rem;
  justify-content: center;
  padding: 0.4rem;
  background: #101024;
  color: #9a9ab8;
}
.viewport-tools button,
.minor {
  background: #26263a;
  color: #ccc;
  border: 1px solid #444;
  border-radius: 6px;
  padding: 0.2rem 0.6rem;
  margin-right: 0.3rem;
  cursor: pointer;
}
.tabs {
  display: flex;
  gap: 0.3rem;
}
.tabs button {
  flex: 1;
  background: #1f1f36;
  color: #9a9ab8;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 0.3rem 0;
  cursor: pointer;
}
.tabs button.active {
  background: #3a5a78;
  color: #fff;
  border-color: #3a5a78;
}
.panel {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  padding-top: 0.5rem;
}
.row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: space-between;
}
.row > span:first-child {
  color: #b8b8d0;
  min-width: 5.5em;
}
.row.slider input[type='range'] {
  flex: 1;
  accent-color: #4fd1c5;
}
.row code {
  min-width: 3.4em;
  text-align: right;
  color: #8fa3b8;
}
.row.radio {
  justify-content: flex-start;
}
.note {
  color: #67678a;
  font-size: 0.75rem;
  font-style: italic;
  margin: 0.25rem 0 0;
}
</style>
