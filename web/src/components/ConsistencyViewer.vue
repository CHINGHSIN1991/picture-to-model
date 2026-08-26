<script setup lang="ts">
// Phase 3 Step 3-5:Blender 渲染圖 vs live viewer 同角度並排,校正色彩一致性。
// 左:Cycles 渲染的 preview.webp;右:攝影棚模式 ModelViewer(同 HDRI、
// 同相機角度、同三點打光配置、ACES tone mapping)。
import { ref } from 'vue'
import ModelViewer from './ModelViewer.vue'

interface Pair {
  label: string
  model: string
  preview: string
}

// preview 來源:output/<job_id>/preview.webp,手動複製到 web/public/renders/
const pairs: Pair[] = [
  { label: 'vintage-radio(hard-surface)', model: '/models/model.glb', preview: '/renders/radio.webp' },
  { label: 'fishbowl(reflective)', model: '/models/fishbowl.glb', preview: '/renders/fishbowl.webp' },
  { label: 'coral-mound(organic)', model: '/models/coral.glb', preview: '/renders/coral.webp' },
]
const current = ref(pairs[0])
const reloadKey = ref(0) // 重置視角:remount viewer 回到渲染角度
</script>

<template>
  <div class="consistency-page">
    <div class="toolbar">
      <select v-model="current">
        <option v-for="p in pairs" :key="p.model" :value="p">{{ p.label }}</option>
      </select>
      <span class="hint">同角度並排;右側可拖曳檢視,按「重置視角」回到渲染角度</span>
      <button @click="reloadKey++">重置視角</button>
    </div>
    <div class="panes">
      <section class="pane">
        <header>Blender Cycles(preview.webp,AgX)</header>
        <div class="content">
          <img :src="current.preview" :alt="current.label" />
        </div>
      </section>
      <section class="pane">
        <header>Three.js live(同 HDRI + 三點打光,ACES)</header>
        <div class="content">
          <Suspense :key="`${current.model}-${reloadKey}`">
            <ModelViewer :url="current.model" studio />
            <template #fallback><p class="loading">載入模型中…</p></template>
          </Suspense>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.consistency-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.4rem 0.75rem;
  background: #16162a;
  font-size: 0.85rem;
}
.toolbar select {
  background: #26263a;
  color: #eee;
  border: 1px solid #444;
  border-radius: 6px;
  padding: 0.25rem 0.5rem;
}
.toolbar button {
  background: #26263a;
  color: #ccc;
  border: 1px solid #444;
  border-radius: 6px;
  padding: 0.25rem 0.6rem;
  font-size: 0.8rem;
  cursor: pointer;
}
.toolbar button:hover {
  background: #3a3a6a;
  color: #fff;
}
.hint {
  color: #666;
  font-size: 0.8rem;
  flex: 1;
}
.panes {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: #000;
  min-height: 0;
}
.pane {
  display: flex;
  flex-direction: column;
  background: #fff; /* 兩側都用白底,與 preview 合成背景一致 */
  min-width: 0;
}
.pane header {
  padding: 0.3rem 0.75rem;
  background: #101020;
  color: #9a9ab8;
  font-size: 0.75rem;
}
.content {
  flex: 1;
  position: relative;
  min-height: 0;
}
.content img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain; /* 1600px 正方形,等比縮放置中 */
  background: #fff;
}
.loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #888;
}
</style>
