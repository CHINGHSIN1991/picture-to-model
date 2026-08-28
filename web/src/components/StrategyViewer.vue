<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import ModelViewer from './ModelViewer.vue'
import { createCameraSync } from './cameraSync'

// /models/variants.json 由 cleanup_model.py --variants 產生,
// 檔案路徑一律相對於 /models/
interface Variant {
  strategy: string
  label?: string // 如 "collapse 10k",同策略多目標面數時區分用
  file: string
  tris_before: number
  tris_after: number
  bytes: number
  params: Record<string, number>
}
interface BaseEntry {
  source: string
  target_tris: number
  variants: Variant[]
}
type Manifest = Record<string, BaseEntry>

const STRATEGY_LABELS: Record<string, string> = {
  collapse: 'Collapse(邊塌縮)',
  planar: 'Planar(平面合併)',
  unsubdiv: 'Un-Subdivide(反細分)',
}
const STRATEGY_HINTS: Record<string, string> = {
  collapse: '塌縮最短邊直到目標面數:面數可控、保 UV,通用預設',
  planar: '合併夾角小於容差的共面區域:hard-surface 效果好,面數不可直接控',
  unsubdiv: '反向細分:只對規則 quad 網格有效,AI 生成的三角網格通常會失敗',
}

const manifest = ref<Manifest | null>(null)
const loadError = ref(false)
const base = ref<string>('')
const selected = ref<string>('') // 以變體檔名為 key(同策略可有多個目標面數)

onMounted(async () => {
  try {
    const res = await fetch('/models/variants.json')
    if (!res.ok) throw new Error(String(res.status))
    manifest.value = await res.json()
    const names = Object.keys(manifest.value ?? {})
    if (names.length) {
      base.value = names[0]
      selected.value = manifest.value![names[0]].variants[0]?.file ?? ''
    }
  } catch {
    loadError.value = true
  }
})

const entry = computed(() => (manifest.value && base.value ? manifest.value[base.value] : null))
const variant = computed(
  () => entry.value?.variants.find((v) => v.file === selected.value) ?? null,
)
const sourceUrl = computed(() => (entry.value ? `/models/${entry.value.source}` : ''))
const variantUrl = computed(() => (variant.value ? `/models/${variant.value.file}` : ''))

function variantLabel(v: Variant) {
  return v.label ?? STRATEGY_LABELS[v.strategy] ?? v.strategy
}

// 換 base 後選取的檔案不存在,退回第一個變體
watch(base, () => {
  if (entry.value && !entry.value.variants.some((v) => v.file === selected.value)) {
    selected.value = entry.value.variants[0]?.file ?? ''
  }
})

const sync = reactive(createCameraSync())
const wireframe = ref(true) // 減面比較看的是拓撲,預設開結構線

interface Stats {
  triangles: number
  bytes: number | null
}
const stats = reactive<{ left: Stats | null; right: Stats | null }>({ left: null, right: null })
watch(sourceUrl, () => (stats.left = null))
watch(variantUrl, () => (stats.right = null))

const diff = computed(() => {
  if (!stats.left || !stats.right) return null
  const tris = (1 - stats.right.triangles / stats.left.triangles) * 100
  const size =
    stats.left.bytes && stats.right.bytes ? (1 - stats.right.bytes / stats.left.bytes) * 100 : null
  return { tris, size }
})

function fmtStats(s: Stats | null) {
  if (!s) return '載入中…'
  const size = s.bytes == null ? '' : ` · ${(s.bytes / 1024 / 1024).toFixed(1)} MB`
  return `${s.triangles.toLocaleString('en-US')} tris${size}`
}
function fmtPct(p: number) {
  return `${p >= 0 ? '−' : '+'}${Math.abs(p).toFixed(1)}%`
}
function fmtParams(v: Variant) {
  return Object.entries(v.params)
    .map(([k, val]) => `${k}=${val}`)
    .join(', ')
}
</script>

<template>
  <!-- 尚未產生 manifest:給出產生指令 -->
  <div v-if="loadError || (manifest && !Object.keys(manifest).length)" class="empty">
    <p>還沒有減面策略變體。先用 pipeline 產生:</p>
    <pre>uv run scripts/run_blender.py cleanup_model -- \
  --input web/public/models/model_raw.glb \
  --output-high /tmp/high.glb --output-web /tmp/model.glb \
  --variants collapse,planar,unsubdiv \
  --variants-manifest web/public/models/variants.json</pre>
    <p>再把輸出的 <code>model__*.glb</code> 複製到 <code>web/public/models/</code>。</p>
  </div>
  <p v-else-if="!manifest" class="empty">載入 variants.json…</p>

  <div v-else class="strategy-page">
    <div class="control-bar">
      <select v-if="Object.keys(manifest).length > 1" v-model="base">
        <option v-for="name in Object.keys(manifest)" :key="name" :value="name">{{ name }}</option>
      </select>
      <div class="strategy-switch">
        <button
          v-for="v in entry?.variants ?? []"
          :key="v.file"
          :class="{ active: selected === v.file }"
          :title="STRATEGY_HINTS[v.strategy]"
          @click="selected = v.file"
        >
          {{ variantLabel(v) }}
        </button>
      </div>
      <span v-if="variant" class="params">{{ fmtParams(variant) }}</span>
      <label class="wire-toggle">
        <input v-model="wireframe" type="checkbox" />
        結構線模式
      </label>
    </div>

    <div class="diff-bar">
      <span v-if="diff && variant" class="diff">
        {{ variantLabel(variant) }} vs 原始:面數 {{ fmtPct(diff.tris) }}<template v-if="diff.size != null">、檔案 {{ fmtPct(diff.size) }}</template>
      </span>
      <span v-else class="diff placeholder">載入比較數據中…</span>
    </div>

    <div class="compare">
      <section class="pane" @pointerenter="sync.active = 'left'" @pointerdown="sync.active = 'left'">
        <span class="pane-label">原始 {{ entry?.source }} · {{ fmtStats(stats.left) }}</span>
        <Suspense>
          <ModelViewer :key="sourceUrl" :url="sourceUrl" :sync="sync" pane-id="left" :wireframe="wireframe" @loaded="(s) => (stats.left = s)" />
          <template #fallback><p class="loading">載入模型中…</p></template>
        </Suspense>
      </section>
      <section class="pane" @pointerenter="sync.active = 'right'" @pointerdown="sync.active = 'right'">
        <span class="pane-label">{{ variant?.file }} · {{ fmtStats(stats.right) }}</span>
        <Suspense>
          <ModelViewer v-if="variantUrl" :key="variantUrl" :url="variantUrl" :sync="sync" pane-id="right" :wireframe="wireframe" @loaded="(s) => (stats.right = s)" />
          <template #fallback><p class="loading">載入模型中…</p></template>
        </Suspense>
      </section>
    </div>
  </div>
</template>

<style scoped>
.strategy-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.empty {
  padding: 2rem;
  color: #9a9ab8;
  font-size: 0.9rem;
}
.empty pre {
  background: #101020;
  border: 1px solid #26263a;
  border-radius: 6px;
  padding: 0.75rem 1rem;
  overflow-x: auto;
  color: #7ee0a3;
}
.control-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.4rem 0.75rem;
  background: #16162a;
  font-size: 0.85rem;
}
.control-bar select {
  background: #26263a;
  color: #eee;
  border: 1px solid #444;
  border-radius: 6px;
  padding: 0.2rem 0.4rem;
}
.strategy-switch {
  display: flex;
  border: 1px solid #444;
  border-radius: 6px;
  overflow: hidden;
}
.strategy-switch button {
  background: #1c1c30;
  color: #aaa;
  border: none;
  padding: 0.3rem 0.75rem;
  font-size: 0.85rem;
  cursor: pointer;
}
.strategy-switch button.active {
  background: #3a3a6a;
  color: #fff;
}
.params {
  color: #666;
  font-size: 0.78rem;
}
.wire-toggle {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  color: #9a9ab8;
  font-size: 0.8rem;
  cursor: pointer;
  user-select: none;
}
.wire-toggle input {
  accent-color: #4fd1c5;
}
.diff-bar {
  padding: 0.35rem 0.75rem;
  text-align: center;
  background: #101020;
  border-bottom: 1px solid #26263a;
  font-size: 0.85rem;
}
.diff {
  color: #7ee0a3;
  font-weight: 600;
  white-space: nowrap;
}
.diff.placeholder {
  color: #555;
}
.compare {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: #000;
  min-height: 0;
}
.pane {
  position: relative;
  background: #1a1a2e;
  min-width: 0;
}
.pane-label {
  position: absolute;
  top: 0.5rem;
  left: 0.5rem;
  z-index: 1;
  background: rgba(16, 16, 32, 0.75);
  border-radius: 4px;
  padding: 0.15rem 0.5rem;
  font-size: 0.75rem;
  color: #9a9ab8;
  pointer-events: none;
}
.loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #888;
}
</style>
