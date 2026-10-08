# Pipeline 總覽

## 影片的完整流程

```
① 決定主題
   ↓
② Astra 產多張 Concept Images          → Step 01
   ↓
③ 選一張 reference                      → Step 02
   ↓
④ Codex 分析建模方式                    → Step 02
   ↓
⑤ Blender Graybox                       → Step 03
   ↓
⑥ Render 多角度檢查                     → Step 03
   ↓
⑦ Blender Detail / Material             → Step 04
   ↓
⑧ 再次 Render + 修正                    → Step 05
   ↓
⑨ Export GLB                            → Step 06
   ↓
⑩ 驗證 GLB                              → Step 06
   ↓
⑪ Three.js Viewer                       → Step 07
   ↓
⑫ Web lighting 調整                     → Step 08
   ↓
⑬ 產網站 Mockup Images                  → Step 09
   ↓
⑭ Vue / React 實作網站                  → Step 10
   ↓
⑮ Three.js 整合                         → Step 10
   ↓
⑯ Mouse interaction                     → Step 11
   ↓
⑰ Scroll animation                      → Step 12
   ↓
⑱ 模型拆解 / 重組 animation             → Step 13
   ↓
⑲ Mobile static fallback                → Step 14
   ↓
⑳ Offscreen pause                       → Step 15
   ↓
㉑ 效能 audit                            → Step 16, 17
   ↓
完成
```

這也是 `cth9191/blender-to-web` 描述的主線:
concept → graybox → detailed model → export → browser interaction → visual comparison → verification。

## 本專案的調整版

因為本專案的目標是「圖片 → Blender 3D → 可調材質/光線 → 放入網站」的**平台**,
所以不照影片原樣做,而是:

```
Image generation
       ↓
Reference image
       ↓
Blender Agent Studio
       ↓
.blend + reproducible .py        ← 關鍵差異
       ↓
GLB
       ↓
Validation pipeline
       ↓
Vue 3 + Three.js viewer
       ↓
材質控制 / 光源控制 / 相機控制   ← 全部是可序列化 config
       ↓
GSAP ScrollTrigger
       ↓
Web Optimization
```

### 關鍵差異 1:一定要保存 Blender Python source

不是只留 `.blend`。這樣未來平台才能做到:

```
使用者:「珊瑚再多一點」
       ↓
AI 修改 Python
       ↓
重新生成 Blender
       ↓
重新 export GLB
       ↓
網頁自動 reload
```

而不是每次從頭做一個不可重現的 Blender 檔案。
Blender Agent Studio 本身也是以保留 `.blend` + Python source 作為核心設計。

對應:Step 03、04、05、06 每一步都要求 `.py` 可從空場景重現。

### 關鍵差異 2:所有網頁端參數可序列化

Step 08 的 lighting、Step 10 的 materials / camera、Step 12 的 sections 全部是 plain object。
未來平台的 UI 只要編輯這些 JSON,場景就會跟著變。

### 關鍵差異 3:Vue 3 + Vite,Three.js 與 UI 分離

不照抄影片 sample 的結構。`src/three/` 是獨立模組,Vue 只透過一個 composable 存取。

## 未來平台的 regenerate loop(預想)

```
┌─────────────────────────────────────────────────────┐
│  Web UI                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐ │
│  │ 材質控制 │  │ 光源控制 │  │ 相機控制 │  │ 文字指令│ │
│  └────┬────┘  └────┬────┘  └────┬────┘  └───┬────┘ │
│       │            │            │            │      │
│       ▼            ▼            ▼            ▼      │
│   materials.json lighting.json camera.json   │      │
│       │            │            │            │      │
│       └────────────┴─────┬──────┘            │      │
│                          ▼                   │      │
│                   Three.js viewer 即時套用    │      │
└──────────────────────────────────────────────┼──────┘
                                               │
                     ┌─────────────────────────▼─────┐
                     │  AI agent (Codex + BAS)        │
                     │  修改 blender/scripts/*.py     │
                     │  → blender --background --python│
                     │  → export GLB                  │
                     │  → validate                    │
                     └─────────────────┬──────────────┘
                                       │
                                       ▼
                             web/public/models/reef.glb
                                       │
                                       ▼
                               Vite HMR / reload
```

## 來源

- 影片:GPT 6 Astra + Blender = INSANE 3D Websites
- 影片使用的專案:https://github.com/cth9191/blender-to-web
- Blender Agent Studio:https://github.com/ifBars/blender-agent-studio
