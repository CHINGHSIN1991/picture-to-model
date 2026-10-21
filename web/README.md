# Picture to Model web — Step 07–17

Vue 3 + Vite + TypeScript + Three.js。`/` 是產品 landing page(Step 10),
`/viewer.html` 是只用來檢查 `export/reef.glb` 的模型檢視頁(Step 07–08)。

```bash
cd web
bun install --frozen-lockfile
bun run dev
```

開啟終端機顯示的 localhost 網址看 landing page;加上 `/viewer.html` 看模型檢視頁
(拖曳旋轉、滾輪縮放、右鍵平移；觸控使用單指旋轉、雙指縮放／平移)。

`dev` 與 `build` 都先將 `../export/reef.glb` 複製至 `public/models/reef.glb`。
如果來源不存在，先依 Step 06 重新匯出；模型副本、依賴與 build 產物不納入 Git。

## Landing page(Step 10)

依 [mockups/final-homepage.png](../mockups/final-homepage.png) 與 [SECTIONS.md](../mockups/SECTIONS.md) 實作，
六個 section 一個元件，模型隨游標微幅傾斜，並由捲動驅動位置、旋轉、相機及零件動畫。

- `src/App.vue`：固定在最底層的 `.stage` canvas 容器 + 六個 section；只透過 `useThreeScene()` 接觸 3D。
- `src/components/`：`SiteNav`、`HeroSection`、`UploadSection`、`ModelSection`、`ControlsSection`、`InteractionSection`、`CtaSection`。
- `src/composables/useThreeScene.ts`：Vue ↔ Three 的唯一橋接，回傳 `status` 與 `setSectionState / setPointer / pause / resume`。
- `src/three/Scene.ts`：renderer、場景、相機、render loop、生命週期；接收 container 與數值，將指標偏移加在 section 角度上。
- `src/three/VisibilityController.ts`：合併內容區域、分頁可見性與手動暫停條件；只控制本場景。
- `src/three/InteractionController.ts`：window 指標事件、時間校正阻尼、離開／失焦回正、動態偏好與事件清理。
- `src/three/ScrollController.ts`：六個 ScrollTrigger、plain state 插值、停留距離、hash 導覽、resize 與 reduced-motion。
- `src/three/PartAnimator.ts`：由 config 選擇零件動作，保存 rest transform、各自阻尼、固定順序與 stagger。
- `src/three/ModelInstances.ts`：依 parent / geometry / material 合批，保留 named transform proxy，更新 instance matrix 與 bounds。
- `src/three/Model.ts`：載入 GLB，依 PROJECT_SPEC 的 part groups 建 `parts` / `groups` 索引，保留原始 pivot，`setMaterialParam`。
- `src/three/CameraController.ts`：Hero 取景（方位 −12°、仰角依 section）、窄螢幕自動拉遠並把模型放到下半部。
- `src/three/config/`：`sections.ts`（SECTIONS.md 1:1）、`partGroups.ts`、`partAnimations.ts`（PROJECT_SPEC，Step 13 用）。全部是 plain object；材質參數沿用 `lightingConfig.ts` 的 `material`。
- `src/landing.css`：版面與產品 UI 道具樣式；canvas `position: fixed; pointer-events: none`，section 疊在上面。

開發用參數：`/?state=3` 固定第 3 段的完成狀態（含零件），不綁 scroll；`/?debug` 開調光面板。
僅 dev 模式的 `/?inspect` 提供唯讀 `window.__reefScene` 快照（狀態、實際角度、零件變換、draw calls、rendering 暫停狀態／累計繪製幀數／水光時間／最後 delta），供測試與截圖腳本使用。
`src/assets/final-concept-800.webp` 是第 2 段的輸入卡片，從保留的 `final-concept-800.jpg` 以 quality 0.85 重編碼。
可用 `bun run encode:concept` 重建；圖片保留原尺寸並使用 lazy / async decoding。

```bash
bun run inspect:landing          # 需另一個終端機跑 bun run dev
LANDING_STATES=2,3,4 bun run inspect:landing
```

以已安裝的 Chrome 與實際 GPU 截 `screenshots/landing-hero.png`、`landing-full.png`、`landing-mobile.png`，
量 5 秒 FPS，並寫 `landing-report.json`。

## 模型檢視頁程式位置（`/viewer.html`）

- `src/pages/Viewer.vue`：掛載、卸載、載入與錯誤提示。
- `src/three/createRenderer.ts`：sRGB、ACES，從 `config/renderer.ts` 取得 DPR 上限 1.5 與 antialias 設定。
- `src/three/rendererResolution.ts`：共用有效 DPR 計算與 resolution media query 監聽；landing / viewer 都在清理時解除監聽。
- `src/three/createScene.ts`：建立場景。
- `src/three/lightingConfig.ts`：可序列化的曝光、燈光、霧氣、水色與材質設定。
- `src/three/createLighting.ts`：三點光、環境反射、陰影、霧氣與背景的生命週期。
- `src/three/createWaterBackground.ts`：漸層水色與柔和光束。
- `src/three/createWaterMaterials.ts`：水紋 shader、共用珊瑚發光材質。
- `src/three/createLightingDebug.ts`：僅 `?debug` 動態載入的 lil-gui 與 stats.js。
- `src/three/loadModel.ts`：GLTFLoader、置中、console hierarchy、共享資源釋放。
- `src/three/Viewer.ts`：PerspectiveCamera、OrbitControls、尺寸調整、render lifecycle。
- `src/three/framing.ts`：兩個頁面共用的取景計算（頂點投影到相機基底、求最小距離）。

主視角取自 `blender/scripts/02_detail.py`，使用相同方位、仰角、鏡頭與 target；
以實際頂點計算窄螢幕所需相機距離，保留完整沙地和潛水員。
置中只移動 GLTFLoader 的包裝節點，GLB 內部零件的 pivots 與 local transforms 保留。

## 水下調光（Step 08）

一般預覽：`http://127.0.0.1:5173/viewer.html`

調光面板：`http://127.0.0.1:5173/viewer.html?debug`（landing page 也接受 `/?debug`）

面板可調曝光、環境反射、光源顏色／強度／位置、陰影、霧氣、水色、水光與材質。
按「輸出設定至 Console」取得完整 JSON；確認後將值回寫 `lightingConfig.ts`。
「還原設定」回到本次載入的預設值。參數不會自動寫入磁碟，重新整理會重設。
移除 `?debug` 並重新整理即可關閉面板與 FPS 顯示，正常頁面不載入這兩項工具。

環境反射由內建 RoomEnvironment 產生一次 128px PMREM，不需要外部 HDR。
霧氣的 near/far 以主視角距離為基準，隨相機距離一起移動，避免手機拉遠時模型被霧完全遮住。
水光是低成本的程序紋理與背景光束，沒有使用 bloom 或體積光後處理。
系統啟用「減少動態效果」時，水紋與光束停在當前相位。

GLB 幾何、貼圖、階層與 transform 不變；瀏覽器將材質分成一般／珊瑚兩份，
仍共用同一張色票。僅 Branch、Brain、Tube 珊瑚使用微量發光。
模型檢視頁的陰影在載入和調光後更新；landing 另外在傾斜、section 狀態或零件變換改變時刷新陰影，停止後不重算。

## 滑鼠互動（Step 11）

`src/three/config/pointer.ts` 支援 `mode: 'tilt' | 'none'`，最大 X / Y 偏移為 0.08 / 0.15 rad。
`damping: 0.08` 是每個 60 Hz frame 的補間比例，`stiffness: 1` 是反應速度倍率；
以 delta time 換算，30 / 60 / 120 Hz 下的一秒響應一致，不會超越最大角度。
魚群避讓是 PROJECT_SPEC 選配，本步未加入。

監聽 window 的 mouse / pen pointer，不攔截 canvas、wheel 或觸控手勢。
游標離開、取消、視窗失焦或分頁隱藏時朝中性回正；DOM 元素間的移動不會誤觸回正。
`prefers-reduced-motion` 切換會立即清除偏移，純觸控裝置停用；卸載時移除所有監聽。

```bash
bun run inspect:pointer          # 需另一個終端機跑 bun run dev
```

輸出 `screenshots/pointer-*.png`（中性、四角、回正）與 `pointer-report.json`。
使用實際 Chrome GPU，在持續移動指標、更新陰影與水光的情況下取樣 5 秒。

## 捲動敘事與逐件動畫（Step 12–13）

`ScrollController` 以每段一個 `scrub: true` ScrollTrigger tween 純數值物件。
每個 `.story-step` 的區間從 top bottom 到 bottom bottom，與前後段銜接、不重疊。
四個有 `partsOnEnter` 的 section 多出一個 viewport 的高度，以 CSS sticky 保持文案就位，
先移動整座模型，再用停留距離播放零件；手機內容較高時，會先捲完內容才停留。
reduced-motion 取消停留距離並直接套段落完成狀態，偏好切換、resize、字型載入都會重新計算。
hash 連結以外層 wrapper 定位，避免 sticky 元素的位置影響導覽。

`PartAnimator` 保留 rest transform，從 config 選擇 `stack / grow / path / orbit`，另有 `explode` 用來驗證換 mode。
rocks 依 bounding box 高度由低至高進場，珊瑚與海草使用固定亂數順序；總 stagger 上限 0.8。
每個零件使用自己的指數阻尼進度，曲線與向量在初始化準備；`t=0` 精確還原 transform。
`hideAtDeparture` 讓指定群組在離場尾端縮小到不可見，魚群轉完 2π 後也能保持尚未進場的狀態。

`ModelInstances` 在材質準備與取景後合批：相同 parent / geometry / material，至少四件才轉換。
75 個零件形成 12 個 InstancedMesh，模型繪製物件 91 → 28。
原 node 留在階層中作不可見代理，讓 group、名稱與原點索引仍可用；動畫更新代理後同步 instance matrix，並重算 bounds。
固定視角含陰影的 `renderer.info.render.calls` 為 182 → 56，面數相同。

```bash
bun run inspect:scroll           # 需另一個終端機跑 bun run dev；需 dev 的 ?inspect 快照
```

輸出六段末態與四段中間態截圖、`scroll-contact-sheet.png`、`instances-before/after.png`、
`scroll-mobile.png` 與 `scroll-report.json`。量測包含水光、陰影與零件動畫下的 5 秒完整往返捲動。

## 靜態 fallback 與可見性（Step 14–15）

`useRenderMode` 在啟動時決定 live / static；小型觸控裝置、減少動態效果、省流量、WebGL 不可用或低效能訊號會使用 WebP。
`?mode=live` / `?mode=static` 可覆寫；靜態模式不載入 Three、GSAP、GLB，也不建立可見性控制器。
細節與生成方式見 [Step 14](../summary/14-mobile-fallback.md)。

Live 場景透過 IntersectionObserver 觀察六個 `[data-has-3d]` wrapper，包含 sticky 停留距離。
只要任一區域可見、document 為 visible、且未手動暫停，才啟動 Scene loop。
`useThreeScene().resume()` 解除手動條件，仍須滿足兩個可見性條件；切換事件不會互相覆蓋暫停原因。
暫停前以零 delta 同步最後畫面，恢復首幀也從零 delta 開始；水光、零件與指標阻尼都不補跑隱藏時間。

目前六段都有 3D，包含 CTA footer。測試腳本另外插入純文字區域測試離屏，正式網站沒有這段內容。
ScrollTrigger 保持事件驅動更新，沒有停止全域 GSAP ticker，因此其他元件動畫照常運作。
獨立 `/viewer.html` 不使用這個 landing 可見性控制器。

```bash
bun run inspect:visibility       # 先跑 bun run dev；使用有桌面環境的 Chrome
```

預設 Chrome 路徑為 macOS 安裝位置，可用 `CHROME_PATH` 覆寫，`VIEWER_URL` 指定 dev server。
腳本使用獨立暫存 profile 與 CDP `noDefaults` 避開 Playwright 的強制 focus，實際切換分頁並記錄 trace。
結果是 `screenshots/visibility-report.json`、`visibility-contact-sheet.png` 與 `visibility-trace.json.gz`。
將 trace 解壓後匯入 DevTools Performance，對照 User Timing 標記與 Three.js `onAnimationFrame`。

## DPR 上限（Step 16）

`src/three/config/renderer.ts` 是初始化、landing resize、viewer resize 的唯一設定來源。
預設 `maxPixelRatio: 1.5`、`antialias: true`、`powerPreference: 'default'`，保留既有渲染偏好。
使用 `min(devicePixelRatio, maxPixelRatio)`，低 DPR 不會被放大。

window resize 與 ResizeObserver 繼續更新尺寸；resolution media query 處理 CSS 尺寸不變的 DPR 變更，
每次通知後改為監聽新的 DPR。沒有輪詢；Scene 暫停時不會因更新 buffer 而啟動 render loop。
目前沒有 FPS 自動降級或裝置專屬上限，靜態裝置分流沿用 Step 14。

```bash
bun run inspect:resolution       # 先跑 bun run dev；VIEWER_URL 可指定其他 port
```

腳本用 Chrome CDP 在固定 CSS 尺寸下切換 DPR，核對 canvas 與 WebGL drawing buffer，
輸出 `screenshots/resolution-report.json` 與 `resolution-contact-sheet.png`。
CDP 需交替 screen / default media override 才會通知既有 resolution 查詢；沒有手動派送 resize。
這是裝置模擬，不是實體跨螢幕測試；像素減量不代表等比例的 GPU 耗時下降。

## 效能 Audit 與漸進載入（Step 17）

Live 的 `loading` / `error` 狀態也顯示既有 `FallbackStill`；Scene 同步畫完第一幀才回報 ready，
Vue Transition 在 200 ms 內淡出圖片，減少動態效果時直接移除。失敗時保留圖片與錯誤訊息。
圖片壓縮降低 static 下載；漸進載入則增加 live 下載，數字與取捨見 [PERFORMANCE.md](PERFORMANCE.md)。

```bash
bun run build
bun run preview --port 4180 --strictPort
# 另一個終端機；依序執行，避免量測互相干擾
bun run audit:performance after
bun run audit:lighthouse after
# audit:visual 另需 5177 dev server
bun run audit:visual
```

報告在 `reports/performance/`，Lighthouse HTML 以 gzip 儲存。
手機 Lighthouse 三次 100 分、LCP 約 1.579 秒、CLS 0；動態含陰影 draw calls 56 的例外也記錄於報告。

## 驗證

```bash
bun run build
bunx playwright install chromium
bun run test
```

若已安裝 Google Chrome，也可直接使用：

```bash
PLAYWRIGHT_CHANNEL=chrome bun run test
```

測試會自行啟動 `127.0.0.1:4173`。模型檢視頁：GLB SHA-256、全部 node 名稱與父子關係、
面數、滑鼠旋轉與縮放、響應式尺寸、DPR、模型 404、WebGL 不可用，
以及調光面板、設定匯出／重設、減少動畫偏好、卸載清理，共七項。
Landing page：六個 section 順序與標題、固定且不攔截指標的單一 canvas、part group 數量、
捲動後 canvas 不動、nav 連結、`?state=N`、手機寬度無橫向捲動、GLB 404 提示，共三項。
截圖在 `test-results/`，供人工視覺審查；完整效能 audit 見 [PERFORMANCE.md](PERFORMANCE.md)。

`tests/pointer.spec.ts` 另外三項測試驗證阻尼、更新頻率一致性、角度上限、離開／失焦回正、
停用模式、觸控裝置、非零 section 角度上的實際畫面變化、動態偏好即時切換、捲動及 nav。
`tests/scroll.spec.ts` 三項涵蓋六段插值與停留、捲回 Hero 的精確還原、pointer 疊加、deep link、
resize、動態偏好、清理，以及 instancing 前後 draw calls / transform / 像素誤差、換 mode 與 stagger。
`tests/fallback.spec.ts` 三項驗證模式判斷、靜態下載與模式覆寫。
`tests/visibility.spec.ts` 三項驗證離屏、可見性條件交錯、背景載入、最後一幀、零 delta 恢復與清理。
`tests/resolution.spec.ts` 三項涵蓋兩入口的初始化、viewport／容器 resize、連續 DPR 變更、antialias、暫停與清理。
Step 17 在 landing 新增一項延遲 GLB 的漸進載入驗證；總計 **26 項**。

在另一個終端機保持 `bun run dev` 運作，再執行：

```bash
bun run inspect:lighting
```

此腳本使用已安裝的 Chrome 和預設 GPU 選擇，暖機 2 秒、取樣 10 秒，
保存桌機／手機／調光面板截圖與 GPU、FPS、檔案 hashes 至 `screenshots/`。
可用 `VIEWER_URL` 指向其他 port 或 production preview，用 `VIEWER_HEADED=1` 顯示瀏覽器視窗。
本次 Apple M4 / Metal、1440×900、DPR 1.5、開啟動畫與面板：平均 **60.0 FPS**，
p95 frame interval **16.8 ms**；詳細條件見 [lighting-report.json](screenshots/lighting-report.json)。
這是該硬體的短時間量測，不代表所有桌機／手機的效能。

TypeScript 固定為 5.9.3，因為本次安裝的 TypeScript 7 與 vue-tsc 3.3.13 不相容。
GSAP 與 ScrollTrigger 已用於 landing page。
Step 12–13 build：landing chunk 約 138 kB（gzip 約 54 kB）、共用 chunk 約 691 kB（gzip 約 184 kB），debug chunk 約 35.5 kB（gzip 約 10.1 kB）；
Vite 仍會提示主 chunk 超過 500 kB，
Step 14–17 已將 3D 隔離為 live 才載入的動態 chunk，最新下載實測見 PERFORMANCE.md。

## 網站 Mockup 截圖(Step 09)

```bash
bun run mockups            # 全部
bun run mockups homepage-01
```

用已安裝的 Chrome 開啟 `../mockups/src/homepage-0N.html`,輸出整頁 PNG 到 `../mockups/`
(桌機 1440 寬與手機 390 寬各一張)並寫 `render-report.json`。
HTML 參照 `blender/renders/mockup/` 的透明 render,先跑 `blender/scripts/04_mockup_renders.py`。

## 視覺基準

基準見 [Step 07 總結](../summary/07-minimal-threejs-viewer.md)，
調光後見 [Step 08 總結](../summary/08-web-lighting.md)。
Blender 使用 AgX / Medium High Contrast，本頁使用 ACES；本步以 concept 的藍色水域、
上方入光、珊瑚對比為方向，不要求與 Blender 逐像素相同。

參考：[Three.js OrbitControls](https://threejs.org/docs/pages/OrbitControls.html)、
[Vite](https://vite.dev/guide/)、
[lil-gui](https://lil-gui.georgealways.com/)、
[Three.js Fog](https://threejs.org/docs/pages/Fog.html)、
[stats.js](https://github.com/mrdoob/stats.js)。
