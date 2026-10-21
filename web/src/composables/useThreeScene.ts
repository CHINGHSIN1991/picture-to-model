import { onBeforeUnmount, onMounted, readonly, ref, type Ref } from 'vue'
import { mountScene, type SceneHandle, type SceneOptions } from '../three/Scene'
import type { SectionState } from '../three/config/sections'

export type SceneStatus = 'loading' | 'ready' | 'error'

/**
 * The single bridge between Vue and Three.js. Components never receive Three objects;
 * they get a status and a handful of functions that take plain values.
 */
export function useThreeScene(container: Ref<HTMLElement | undefined>, options: SceneOptions = {}) {
  const status = ref<SceneStatus>('loading')
  const message = ref('')
  let handle: SceneHandle | undefined

  onMounted(() => {
    if (!container.value) return
    try {
      handle = mountScene(container.value, options)
      void handle.ready.then(() => {
        status.value = 'ready'
      }).catch(fail)
    } catch (error) {
      fail(error)
    }
  })

  function fail(error: unknown) {
    console.error('[reef-landing]', error)
    status.value = 'error'
    message.value = '3D 場景無法顯示。請確認模型檔案、網路連線及瀏覽器 WebGL 支援，然後重新整理。'
  }

  onBeforeUnmount(() => {
    handle?.dispose()
    handle = undefined
  })

  return {
    status: readonly(status),
    message: readonly(message),
    setSectionState: (state: SectionState) => handle?.setSectionState(state),
    setPointer: (x: number, y: number) => handle?.setPointer(x, y),
    pause: () => handle?.pause(),
    resume: () => handle?.resume(),
  }
}
