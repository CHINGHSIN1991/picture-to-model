<script setup lang="ts">
import { ref } from 'vue'
import ModelViewer from './components/ModelViewer.vue'

// 把 GLB 放到 web/public/models/ 後在這裡列出
const models = ref<string[]>(['/models/model_raw.glb'])
const current = ref(models.value[0])
</script>

<template>
  <div class="viewer-page">
    <header>
      <h1>Picture to Model — Viewer</h1>
      <select v-model="current">
        <option v-for="m in models" :key="m" :value="m">{{ m.split('/').pop() }}</option>
      </select>
    </header>
    <main>
      <Suspense>
        <ModelViewer :key="current" :url="current" />
        <template #fallback>
          <p class="loading">載入模型中…</p>
        </template>
      </Suspense>
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
header select {
  background: #26263a;
  color: #eee;
  border: 1px solid #444;
  border-radius: 6px;
  padding: 0.25rem 0.5rem;
}
main {
  flex: 1;
  position: relative;
}
.loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #888;
}
</style>
