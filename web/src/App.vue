<script setup lang="ts">
import { ref } from 'vue'
import ModelViewer from './components/ModelViewer.vue'
import CompareViewer from './components/CompareViewer.vue'
import ConsistencyViewer from './components/ConsistencyViewer.vue'
import EditorView from './components/EditorView.vue'
import EmbedViewer from './components/EmbedViewer.vue'
import StrategyViewer from './components/StrategyViewer.vue'
import { MODELS } from './modelList'

const models = ref<string[]>(MODELS)
const current = ref(models.value[0])
// ?mode=compare / consistency / strategy / editor 可深連結;embed 為無 chrome 的嵌入頁
type Mode = 'single' | 'compare' | 'consistency' | 'strategy' | 'editor' | 'embed'
const initialMode = new URLSearchParams(location.search).get('mode')
const mode = ref<Mode>(
  initialMode === 'compare' ||
    initialMode === 'consistency' ||
    initialMode === 'strategy' ||
    initialMode === 'editor' ||
    initialMode === 'embed'
    ? initialMode
    : 'single',
)
</script>

<template>
  <!-- 🎯 Embed:主產出的嵌入頁,不帶任何 app chrome -->
  <EmbedViewer v-if="mode === 'embed'" />
  <div v-else class="viewer-page">
    <header>
      <h1>Picture to Model — Viewer</h1>
      <nav class="mode-switch">
        <button :class="{ active: mode === 'single' }" @click="mode = 'single'">單一檢視</button>
        <button :class="{ active: mode === 'compare' }" @click="mode = 'compare'">比較模式</button>
        <button :class="{ active: mode === 'consistency' }" @click="mode = 'consistency'">一致性驗證</button>
        <button :class="{ active: mode === 'strategy' }" @click="mode = 'strategy'">減面策略</button>
        <button :class="{ active: mode === 'editor' }" @click="mode = 'editor'">編輯器</button>
      </nav>
      <select v-if="mode === 'single'" v-model="current">
        <option v-for="m in models" :key="m" :value="m">{{ m.split('/').pop() }}</option>
      </select>
      <span v-else-if="mode === 'compare'" class="hint">拖曳任一側旋轉,兩邊視角同步</span>
      <span v-else-if="mode === 'consistency'" class="hint">Blender 渲染圖 vs live viewer,校正色彩一致性</span>
      <span v-else-if="mode === 'strategy'" class="hint">同一高模、不同 decimate 策略,左原始右變體視角同步</span>
      <span v-else class="hint">Scene Editor(4B 前端 MVP)— 滑桿即時生效,只寫 scene.json</span>
    </header>
    <main>
      <Suspense v-if="mode === 'single'">
        <ModelViewer :key="current" :url="current" />
        <template #fallback>
          <p class="loading">載入模型中…</p>
        </template>
      </Suspense>
      <CompareViewer v-else-if="mode === 'compare'" :models="models" />
      <ConsistencyViewer v-else-if="mode === 'consistency'" />
      <StrategyViewer v-else-if="mode === 'strategy'" />
      <EditorView v-else />
    </main>
  </div>
</template>

<style scoped>
.viewer-page {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: #1a1a2e;
  color: #eee;
}
header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.6rem 1rem;
  background: #12121f;
}
header h1 {
  font-size: 1rem;
  margin: 0;
  font-weight: 600;
}
.mode-switch {
  display: flex;
  border: 1px solid #444;
  border-radius: 6px;
  overflow: hidden;
}
.mode-switch button {
  background: #1c1c30;
  color: #aaa;
  border: none;
  padding: 0.3rem 0.75rem;
  font-size: 0.85rem;
  cursor: pointer;
}
.mode-switch button.active {
  background: #3a3a6a;
  color: #fff;
}
header select {
  background: #26263a;
  color: #eee;
  border: 1px solid #444;
  border-radius: 6px;
  padding: 0.25rem 0.5rem;
}
.hint {
  color: #666;
  font-size: 0.8rem;
}
main {
  flex: 1;
  position: relative;
  min-height: 0;
}
.loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #888;
}
</style>
