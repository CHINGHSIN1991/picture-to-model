<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import ModelViewer from './ModelViewer.vue'
import { createCameraSync } from './cameraSync'

const props = defineProps<{ models: string[] }>()

// 預設:左邊原始模型、右邊優化版
const left = ref(props.models.find((m) => m.includes('raw')) ?? props.models[0])
const right = ref(props.models.find((m) => !m.includes('raw')) ?? props.models[0])

const sync = reactive(createCameraSync())
const wireframe = ref(false)

interface Stats {
  triangles: number
  bytes: number | null
}
const stats = reactive<{ left: Stats | null; right: Stats | null }>({ left: null, right: null })
watch(left, () => (stats.left = null))
watch(right, () => (stats.right = null))

const diff = computed(() => {
  if (!stats.left || !stats.right || !stats.left.triangles) return null
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
</script>

<template>
  <div class="compare-page">
    <!-- 比較結果獨立一列,置中顯示,不與其他內容共用空間 -->
    <div class="diff-bar">
      <span v-if="diff" class="diff">
        右比左:面數 {{ fmtPct(diff.tris) }}<template v-if="diff.size != null">、檔案 {{ fmtPct(diff.size) }}</template>
      </span>
      <span v-else class="diff placeholder">載入比較數據中…</span>
      <label class="wire-toggle">
        <input v-model="wireframe" type="checkbox" />
        結構線模式
      </label>
    </div>

    <!-- 各 pane 的模型選擇與統計 -->
    <div class="compare-bar">
      <div class="side">
        <select v-model="left">
          <option v-for="m in models" :key="m" :value="m">{{ m.split('/').pop() }}</option>
        </select>
        <span class="stats">{{ fmtStats(stats.left) }}</span>
      </div>
      <div class="side right">
        <span class="stats">{{ fmtStats(stats.right) }}</span>
        <select v-model="right">
          <option v-for="m in models" :key="m" :value="m">{{ m.split('/').pop() }}</option>
        </select>
      </div>
    </div>

    <div class="compare">
      <section class="pane" @pointerenter="sync.active = 'left'" @pointerdown="sync.active = 'left'">
        <Suspense>
          <ModelViewer :key="left" :url="left" :sync="sync" pane-id="left" :wireframe="wireframe" @loaded="(s) => { if (s.url === left) stats.left = s }" />
          <template #fallback><p class="loading">載入模型中…</p></template>
        </Suspense>
      </section>
      <section class="pane" @pointerenter="sync.active = 'right'" @pointerdown="sync.active = 'right'">
        <Suspense>
          <ModelViewer :key="right" :url="right" :sync="sync" pane-id="right" :wireframe="wireframe" @loaded="(s) => { if (s.url === right) stats.right = s }" />
          <template #fallback><p class="loading">載入模型中…</p></template>
        </Suspense>
      </section>
    </div>
  </div>
</template>

<style scoped>
.compare-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.diff-bar {
  position: relative;
  padding: 0.35rem 0.75rem;
  text-align: center;
  background: #101020;
  border-bottom: 1px solid #26263a;
  font-size: 0.85rem;
}
.wire-toggle {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
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
.compare-bar {
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  gap: 1rem;
  padding: 0.4rem 0.75rem;
  background: #16162a;
  font-size: 0.8rem;
}
.side {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}
.side.right {
  justify-content: flex-end;
}
.compare-bar select {
  background: #26263a;
  color: #eee;
  border: 1px solid #444;
  border-radius: 6px;
  padding: 0.2rem 0.4rem;
}
.stats {
  color: #9a9ab8;
  white-space: nowrap;
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
.loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #888;
}
</style>
