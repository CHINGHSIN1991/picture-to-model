// 與 Blender 相同的 HDRI(setup_lighting.py 的 DEFAULT_HDRI)。
// 模組層快取:多個 viewer 實例(比較模式)與模型切換共用同一張,只抓一次;
// 載入失敗降級為 null(無 IBL,靠方向光),不讓 Suspense 卡死在載入中。
import type { Texture } from 'three'
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js'

export const HDRI_URL = '/hdri/studio_small_08_1k.hdr'
// 對映 Blender World Background 的 Strength(setup_lighting.py 為 0.4)
export const HDRI_INTENSITY = 0.4

let hdriPromise: Promise<Texture | null> | undefined

export function loadHdri(): Promise<Texture | null> {
  hdriPromise ??= new RGBELoader().loadAsync(HDRI_URL).catch((err) => {
    console.warn(`HDRI 載入失敗(${HDRI_URL}),改用無 IBL 場景`, err)
    return null
  })
  return hdriPromise
}
