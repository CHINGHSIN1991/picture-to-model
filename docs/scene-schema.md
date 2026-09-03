# Scene Schema v0(scene.json)

> 回到主文件:[ROADMAP.md](../ROADMAP.md)
> 定位:Phase 3 與 Phase 4 之間的地基;4B Scene Editor、Embed、poster 渲染的共同語言。
> 🎯 目標(2026-08-26 校正):**主產出是嵌入網站的互動模型**;Cycles 渲染降為 poster / og:image 配角。
> 依據:spec 三方比對(`docs/spec-delta.md`)——GPT 與 Gemini 兩份外部 spec 獨立收斂於「Scene 狀態以 JSON 與 GLB 分離」。
> 原則:**欄位直接從現有實作萃取,不新造概念**;每個欄位都能對映到一支既有腳本的參數。

---

## 為什麼要分離 scene.json 與 GLB

- **變更頻率差三個數量級**:幾何與貼圖內容由 AI 生成,貴而慢(~155s/次、扣 API 額度),一次定案;光照與材質參數由 GPU 每幀重算,隨時免費。把兩者綁在同一個檔案裡,等於每次調滑桿都要動 15MB 的資產。
- **兩個消費者、一份真相**:主消費者是網站內的互動 viewer / Embed(Three.js),配角是 poster 渲染(Blender Cycles)——Web / Blender 一致性從「事後校正」變成「共用參數來源」,且因為瀏覽器畫面就是產品本身,校正瀏覽器 = 校正產品。
- **非破壞性**:`materials_override` 只記差異,GLB 原始材質不動;移除 override 即還原。

---

## Schema v0

```jsonc
{
  "version": 0,
  "model_url": "web/<job_id>/model.glb",            // 既有產物(cleanup 輸出)

  "environment": {
    "hdri": "studio_small_08_1k",                    // 對映 assets/*.hdr(目前一組,之後擴充 preset 庫)
    "intensity": 0.4,                                // = setup_lighting.py 現值
    "rotation": 0,                                   // HDRI 繞垂直軸旋轉(度);additive 欄位(2026-08-26),缺省 = 0
    "background": { "type": "color", "value": "#FFFFFF" }   // color | transparent | environment
  },

  "lights": [                                         // = 程式化三點打光參數化(setup_lighting.py)
    { "id": "key",  "type": "area", "azimuth": 75,  "elevation": 45, "power": 400 },
    { "id": "fill", "type": "area", "azimuth": -30, "elevation": 20, "power": 130 },
    { "id": "rim",  "type": "area", "azimuth": 200, "elevation": 40, "power": 250 }
  ],

  "camera": {                                         // = setup_camera.py 參數面;poster 渲染與 viewer 初始相機共用同一份(避免載入跳動)
    "azimuth": 30, "elevation": 18,
    "focal_mm": 50, "padding": 1.4                   // auto-frame:距離依 bounding box 與 FOV 計算
  },

  "materials_override": {                             // 非破壞性覆寫,key = GLB 內材質名
    "glass": { "transmission": 1.0, "ior": 1.45, "roughness": 0.05 }
    // 允許欄位:base_color_tint / roughness / metallic / emissive / transmission / ior
    // transmission + ior 即 fishbowl 玻璃解法(使用者開啟,取代 AI 偵測)
  },

  "render": {                                         // = render.py 參數面(Render API 直接吃)
    "engine": "cycles", "samples": 128, "resolution": 1600,
    "tone_mapping": "agx", "transparent": true
  }
}
```

## 欄位 → 現有實作對映表

| 欄位 | 現有來源 | Editor 元件 | Blender 端消費者 |
|---|---|---|---|
| `model_url` | cleanup 輸出 `model.glb` | Viewport 載入 | render.py `--input` |
| `environment.*` | `setup_lighting.py` HDRI 段 | Light tab(強度 / 旋轉 / 背景) | build_lighting() |
| `lights[]` | `setup_lighting.py` 三點打光常數 | Scene 樹 + Light tab | build_lighting() |
| `camera.*` | `setup_camera.py` CLI 參數 | Camera tab(preset / FOV / auto-frame);**Embed 初始相機** | frame_camera();**poster 渲染** —— 兩者讀同一份,是避免載入完成時畫面「跳動」的關鍵(見 [phase-4「4B Embed 指南」](phase-4-web-product.md)) |
| `materials_override` | glTF PBR 因子(factor × 貼圖取樣) | Material tab 滑桿 | setup_material 延伸(套 override 後匯出) |
| `render.*` | `render.py` CLI 參數 | poster 按鈕的進階選項 | render.py(--scene-json) |

---

## 資料流

```text
Inspector 滑桿 ──► editor store(單一真相來源;MVP 為 reactive,4A 換 Pinia)
                    ├─► 即時路徑:Three.js 材質 / 燈屬性,即幀生效(零 AI、零成本)✅ 已實作
                    └─► 持久化:scene.json(debounce 寫 localStorage;之後存 scenes 表 JSONB)✅ 已實作
scene.json ────────► Export:gltf-transform 把 materials_override 合成進 GLB(秒級)
            │        (MVP 暫以 three GLTFExporter 於 client 端合成)
            ├──────► poster 渲染(選配):--scene-json → apply_scene.py → Cycles(48.8s)
            │          ✅ CLI 已通(fishbowl transmission 實測渲出真玻璃);產出 = Embed 的
            │          poster(載入佔位)與 og:image,不覆蓋官方 preview.webp
            └──────► 🎯 Embed(主產出):GLB + hdr + scene.json + poster 全為靜態檔
                       → iframe / <model-viewer poster=…> 嵌進任意網站
                       靜態託管今天即可嵌;4A 只是把「手動放檔案」自動化(產生器 + public URL)
                       ✅ 已實作:`?mode=embed&model=&scene=&poster=`(sceneRig.ts 與 editor 共用
                          套用邏輯;poster 佔位淡出;iframe 實嵌宿主頁驗證通過)
```

## 哪些操作需要 AI(分層速查)

| 操作 | 層 | AI | 延遲 |
|---|---|---|---|
| 調光源 / HDRI / 背景 / 材質因子(含 transmission) | scene.json | ✗ | 即時 |
| Export 合成 GLB | gltf-transform | ✗ | 秒級 |
| poster 縮圖(選配;載入佔位 + og:image) | Cycles job | ✗ | ~48.8s |
| 改目標面數 | cleanup 重跑(model_raw 紅利) | ✗ | ~6s |
| 改形狀 / 背面 / 部件 | 重新生成 | ✓ | ~110s |
| 改貼圖「內容」(風格 / 去烘死光影) | texture gen / delighting(P2) | ✓ | — |

---

## 四個支撐機制(2026-08-27 補述)

供文件與簡報共用的敘述;四者合起來就是「為什麼滑桿可以隨便拉、GLB 永遠不會壞」。

1. **非破壞性覆寫**:`materials_override` 以 GLB 材質名為 key、只記差異;移除即還原,GLB 永不改寫。(因此 gltf-transform 的 `--palette` 必須關閉 —— 材質名不能被合併改掉。)
2. **factor × 貼圖語意**:override 以 glTF PBR factor 實作(數值乘在貼圖取樣結果上);Three.js 與 `apply_scene.py` 共用同一套語意 = 兩端一致的前提。
3. **快照式 Undo**:scene.json < 2KB,整份快照進 undo stack(⌘Z、350ms 收束);天然涵蓋 additive 新欄位,新滑桿不用寫新 command。
4. **Additive 版本策略**:`version` 自 0 起、欄位只增不改語意;未知欄位「讀取端忽略、寫入端保留」。`environment.rotation` 為首次演進的向前相容驗證。

## 版本策略

- `version` 欄位自 0 起;欄位只增不改語意(additive),破壞性變更升 major。
- 未知欄位:讀取端忽略、寫入端保留(向前相容)。
- v0 範圍刻意小:單模型、單場景;多物件 Scene / 場景合成屬 Phase 5,屆時擴 `objects[]` 而非改 `model_url` 語意。
