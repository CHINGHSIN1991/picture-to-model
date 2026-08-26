# Scene Schema v0(scene.json)

> 回到主文件:[ROADMAP.md](../ROADMAP.md)
> 定位:Phase 3 與 Phase 4 之間的地基;4B Scene Editor、Render API、Export 的共同語言。
> 依據:spec 三方比對(`docs/spec-delta.md`)——GPT 與 Gemini 兩份外部 spec 獨立收斂於「Scene 狀態以 JSON 與 GLB 分離」。
> 原則:**欄位直接從現有實作萃取,不新造概念**;每個欄位都能對映到一支既有腳本的參數。

---

## 為什麼要分離 scene.json 與 GLB

- **變更頻率差三個數量級**:幾何與貼圖內容由 AI 生成,貴而慢(~155s/次、扣 API 額度),一次定案;光照與材質參數由 GPU 每幀重算,隨時免費。把兩者綁在同一個檔案裡,等於每次調滑桿都要動 15MB 的資產。
- **兩個消費者、一份真相**:瀏覽器即時預覽(Three.js)讀它,高品質渲染(Blender Cycles)也讀它——Web / Blender 一致性從「事後校正」變成「共用參數來源」。
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
    "background": { "type": "color", "value": "#FFFFFF" }   // color | transparent | environment
  },

  "lights": [                                         // = 程式化三點打光參數化(setup_lighting.py)
    { "id": "key",  "type": "area", "azimuth": 75,  "elevation": 45, "power": 400 },
    { "id": "fill", "type": "area", "azimuth": -30, "elevation": 20, "power": 130 },
    { "id": "rim",  "type": "area", "azimuth": 200, "elevation": 40, "power": 250 }
  ],

  "camera": {                                         // = setup_camera.py 參數面
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
| `camera.*` | `setup_camera.py` CLI 參數 | Camera tab(preset / FOV / auto-frame) | frame_camera() |
| `materials_override` | glTF PBR 因子(factor × 貼圖取樣) | Material tab 滑桿 | setup_material 延伸(套 override 後匯出) |
| `render.*` | `render.py` CLI 參數 | Render 按鈕的進階選項 | render.py |

---

## 資料流

```text
Inspector 滑桿 ──► editor store(單一真相來源;MVP 為 reactive,4A 換 Pinia)
                    ├─► 即時路徑:Three.js 材質 / 燈屬性,即幀生效(零 AI、零成本)✅ 已實作
                    └─► 持久化:scene.json(debounce 寫 localStorage;之後存 scenes 表 JSONB)✅ 已實作
scene.json ────────► Export:gltf-transform 把 materials_override 合成進 GLB(秒級)
            │        (MVP 暫以 three GLTFExporter 於 client 端合成)
            └──────► Render API:POST /api/renders {job_id, scene_overrides}
                       → scene.json → setup_lighting / setup_camera / render.py → Cycles(~40s)
                       ✅ CLI 參數面已打通:`render_model.py --scene-json`(apply_scene.py 套
                          materials_override;fishbowl transmission 實測渲出真玻璃,48.8s)
```

## 哪些操作需要 AI(分層速查)

| 操作 | 層 | AI | 延遲 |
|---|---|---|---|
| 調光源 / HDRI / 背景 / 材質因子(含 transmission) | scene.json | ✗ | 即時 |
| Export 合成 GLB | gltf-transform | ✗ | 秒級 |
| 高品質商品圖(新光照重渲) | Cycles job | ✗ | ~40s |
| 改目標面數 | cleanup 重跑(model_raw 紅利) | ✗ | ~6s |
| 改形狀 / 背面 / 部件 | 重新生成 | ✓ | ~110s |
| 改貼圖「內容」(風格 / 去烘死光影) | texture gen / delighting(P2) | ✓ | — |

---

## 版本策略

- `version` 欄位自 0 起;欄位只增不改語意(additive),破壞性變更升 major。
- 未知欄位:讀取端忽略、寫入端保留(向前相容)。
- v0 範圍刻意小:單模型、單場景;多物件 Scene / 場景合成屬 Phase 5,屆時擴 `objects[]` 而非改 `model_url` 語意。
