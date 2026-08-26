// 與 Blender 相同的 HDRI(setup_lighting.py 的 DEFAULT_HDRI)。
// 模組層以 URL 為 key 快取:多個 viewer 實例(比較模式)與模型切換共用同一張,只抓一次;
// 載入失敗降級為 null(無 IBL,靠方向光),不讓 Suspense 卡死在載入中。
import type { Texture } from 'three'
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js'

export const HDRI_URL = '/hdri/studio_small_08_1k.hdr'
// Embed 專用降檔版(388KB vs 1.5MB):PMREM 立方貼圖僅 ~256px,IBL 品質無感;
// 僅在 background 不是 environment(HDRI 不上畫面)時才可安全使用。
export const HDRI_URL_EMBED = '/hdri/studio_small_08_512.hdr'
// 對映 Blender World Background 的 Strength(setup_lighting.py 為 0.4)
export const HDRI_INTENSITY = 0.4

const hdriCache = new Map<string, Promise<Texture | null>>()

export function loadHdri(url: string = HDRI_URL): Promise<Texture | null> {
  let p = hdriCache.get(url)
  if (!p) {
    p = new RGBELoader().loadAsync(url).catch((err) => {
      console.warn(`HDRI 載入失敗(${url}),改用無 IBL 場景`, err)
      return null
    })
    hdriCache.set(url, p)
  }
  return p
}
