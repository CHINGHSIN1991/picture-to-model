<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { mountViewer } from '../three/Viewer'

const viewport = ref<HTMLDivElement>()
const status = ref('正在載入模型…')
const failed = ref(false)
let dispose: (() => void) | undefined

onMounted(() => {
  if (!viewport.value) return
  try {
    const viewer = mountViewer(viewport.value)
    dispose = viewer.dispose
    void viewer.ready.then(() => {
      status.value = ''
    }).catch(showError)
  } catch (error) {
    showError(error)
  }
})

function showError(error: unknown) {
  console.error('[reef-viewer]', error)
  failed.value = true
  status.value = '無法顯示模型。請確認模型檔案、網路連線及瀏覽器 WebGL 支援，然後重新整理。'
}

onBeforeUnmount(() => dispose?.())
</script>

<template>
  <main class="viewer" :data-state="failed ? 'error' : status ? 'loading' : 'ready'">
    <div ref="viewport" class="viewport" />
    <p class="caption">REEF / 模型檢視</p>
    <p v-if="status" class="status" :role="failed ? 'alert' : 'status'">{{ status }}</p>
    <p v-else class="hint">拖曳旋轉 · 滾輪縮放 · 右鍵平移 · 觸控可用雙指縮放與平移</p>
  </main>
</template>
