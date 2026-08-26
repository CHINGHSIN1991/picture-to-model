<script setup lang="ts">
// 🎯 Embed(主產出):極簡可嵌入頁——無 app chrome,iframe 直接嵌任意網站。
//
//   <iframe src=".../?mode=embed&model=<GLB>&scene=<scene.json>&poster=<webp>" …>
//
// poster 作載入佔位(Cycles 渲染圖,與 live 場景同一份 scene.json 參數),
// GLB + HDRI 載入完成後淡出。全部素材都是靜態檔,靜態託管即可。
import { ref } from 'vue'
import EmbedScene from './EmbedScene.vue'

const params = new URLSearchParams(location.search)
const modelUrl = params.get('model') ?? '/models/model.glb'
const sceneUrl = params.get('scene') ?? undefined
const posterUrl = params.get('poster') ?? undefined

const loaded = ref(false)
</script>

<template>
  <div class="embed">
    <Suspense @resolve="loaded = true">
      <EmbedScene :model-url="modelUrl" :scene-url="sceneUrl" />
      <template #fallback>
        <div class="placeholder" />
      </template>
    </Suspense>
    <!-- poster 佔位:蓋在 canvas 上,載入完成淡出 -->
    <img
      v-if="posterUrl"
      :src="posterUrl"
      class="poster"
      :class="{ hidden: loaded }"
      alt=""
      aria-hidden="true"
    />
    <span class="hint" :class="{ hidden: !loaded }">拖曳旋轉 · 滾輪縮放</span>
  </div>
</template>

<style scoped>
.embed {
  position: fixed;
  inset: 0;
  background: #fff;
}
.placeholder {
  position: absolute;
  inset: 0;
  background: #fff;
}
.poster {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #fff;
  transition: opacity 0.4s ease;
  pointer-events: none;
}
.poster.hidden {
  opacity: 0;
}
.hint {
  position: absolute;
  right: 0.75rem;
  bottom: 0.6rem;
  font-size: 0.7rem;
  color: #9aa;
  background: rgba(255, 255, 255, 0.7);
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  opacity: 1;
  transition: opacity 0.4s ease 1.5s;
  user-select: none;
  pointer-events: none;
}
.hint.hidden {
  opacity: 0;
}
</style>
