<script setup lang="ts">
import { ref } from 'vue'
import ModelViewer from './components/ModelViewer.vue'
import CompareViewer from './components/CompareViewer.vue'
import ConsistencyViewer from './components/ConsistencyViewer.vue'

// 把 GLB 放到 web/public/models/ 後在這裡列出
const models = ref<string[]>([
  '/models/model.glb',
  '/models/model_raw.glb',
  '/models/radio_baked.glb',
  '/models/fishbowl.glb',
  '/models/fishbowl_raw.glb',
  '/models/coral.glb',
  '/models/coral_raw.glb',
  '/models/trellis_radio.glb',
])
const current = ref(models.value[0])
// ?mode=compare / ?mode=consistency 可直接深連結到對應模式
type Mode = 'single' | 'compare' | 'consistency'
const initialMode = new URLSearchParams(location.search).get('mode')
const mode = ref<Mode>(
  initialMode === 'compare' || initialMode === 'consistency' ? initialMode : 'single',
)
</script>

<template>
  <div class="viewer-page">
    <header>
      <h1>Picture to Model — Viewer</h1>
      <nav class="mode-switch">
        <button :class="{ active: mode === 'single' }" @click="mode = 'single'">單一檢視</button>
        <button :class="{ active: mode === 'compare' }" @click="mode = 'compare'">比較模式</button>
        <button :class="{ active: mode === 'consistency' }" @click="mode = 'consistency'">一致性驗證</button>
      </nav>
      <select v-if="mode === 'single'" v-model="current">
        <option v-for="m in models" :key="m" :value="m">{{ m.split('/').pop() }}</option>
      </select>
      <span v-else-if="mode === 'compare'" class="hint">拖曳任一側旋轉,兩邊視角同步</span>
      <span v-else class="hint">Blender 渲染圖 vs live viewer,校正色彩一致性</span>
    </header>
    <main>
      <Suspense v-if="mode === 'single'">
        <ModelViewer :key="current" :url="current" />
        <template #fallback>
          <p class="loading">載入模型中…</p>
        </template>
      </Suspense>
      <CompareViewer v-else-if="mode === 'compare'" :models="models" />
      <ConsistencyViewer v-else />
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
