import { nextTick, onBeforeUnmount, onMounted, readonly, ref, type Ref } from 'vue'
import type { SceneHandle, SceneOptions } from '../three/Scene'
import type { SectionState } from '../three/config/sections'
import type { ScrollController } from '../three/ScrollController'
import type { RenderMode } from './useRenderMode'

export type SceneStatus = 'loading' | 'ready' | 'error'

/**
 * The single bridge between Vue and Three.js. Components never receive Three objects;
 * they get a status and a handful of functions that take plain values.
 * In `static` mode nothing is imported: Three.js, GSAP and the GLB never leave the server (Step 14).
 */
export function useThreeScene(container: Ref<HTMLElement | undefined>, options: SceneOptions = {}, story?: Ref<HTMLElement | undefined>, mode: RenderMode = 'live') {
  const status = ref<SceneStatus>(mode === 'static' ? 'ready' : 'loading')
  const message = ref('')
  let handle: SceneHandle | undefined
  let scroll: ScrollController | undefined
  let disposed = false

  onMounted(async () => {
    if (mode === 'static') return
    await nextTick()
    if (disposed) return
    if (!container.value) return
    try {
      const bindScroll = Boolean(story?.value) && !options.state
      // Dynamic imports keep the Three.js and GSAP chunks out of the static page.
      const [{ mountScene }, scrollModule] = await Promise.all([
        import('../three/Scene'),
        bindScroll ? import('../three/ScrollController') : undefined,
      ])
      if (disposed || !container.value) return
      if (scrollModule && story?.value) scroll = new scrollModule.ScrollController(story.value)
      handle = mountScene(container.value, { ...options, stateSource: scroll ? () => scroll!.getState() : undefined })
      if (import.meta.env.DEV && new URLSearchParams(location.search).has('inspect')) {
        Object.defineProperty(window, '__reefScene', { configurable: true, get: () => handle?.inspect() })
      }
      void handle.ready.then(() => {
        if (!disposed) status.value = 'ready'
      }).catch(fail)
    } catch (error) {
      fail(error)
    }
  })

  function fail(error: unknown) {
    if (disposed) return
    scroll?.dispose()
    scroll = undefined
    console.error('[reef-landing]', error)
    status.value = 'error'
    message.value = '3D 場景無法顯示。請確認模型檔案、網路連線及瀏覽器 WebGL 支援，然後重新整理。'
  }

  onBeforeUnmount(() => {
    disposed = true
    scroll?.dispose()
    handle?.dispose()
    handle = undefined
    if (import.meta.env.DEV) Reflect.deleteProperty(window, '__reefScene')
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
