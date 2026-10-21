# Picture to Model web — Step 07–10

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
六個 section 一個元件，模型停在 Hero 狀態；指標與捲動互動留給 Step 11–12。

- `src/App.vue`：固定在最底層的 `.stage` canvas 容器 + 六個 section；只透過 `useThreeScene()` 接觸 3D。
- `src/components/`：`SiteNav`、`HeroSection`、`UploadSection`、`ModelSection`、`ControlsSection`、`InteractionSection`、`CtaSection`。
- `src/composables/useThreeScene.ts`：Vue ↔ Three 的唯一橋接，回傳 `status` 與 `setSectionState / setPointer / pause / resume`。
- `src/three/Scene.ts`：renderer、場景、相機、render loop、生命週期；接收 container 與數值，不碰其他 DOM。
- `src/three/Model.ts`：載入 GLB，依 PROJECT_SPEC 的 part groups 建 `parts` / `groups` 索引，保留原始 pivot，`setMaterialParam`。
- `src/three/CameraController.ts`：Hero 取景（方位 −12°、仰角依 section）、窄螢幕自動拉遠並把模型放到下半部。
- `src/three/config/`：`sections.ts`（SECTIONS.md 1:1）、`partGroups.ts`、`partAnimations.ts`（PROJECT_SPEC，Step 13 用）。全部是 plain object；材質參數沿用 `lightingConfig.ts` 的 `material`。
- `src/landing.css`：版面與產品 UI 道具樣式；canvas `position: fixed; pointer-events: none`，section 疊在上面。

開發用參數：`/?state=3` 直接套第 3 段的模型狀態（位置、旋轉、縮放、相機仰角，零件動畫未實作），`/?debug` 開調光面板。
`src/assets/final-concept-800.jpg` 是 `references/final-concept.png` 縮到 800 px 的版本，給第 2 段的輸入卡片用。

```bash
bun run inspect:landing          # 需另一個終端機跑 bun run dev
LANDING_STATES=2,3,4 bun run inspect:landing
```

以已安裝的 Chrome 與實際 GPU 截 `screenshots/landing-hero.png`、`landing-full.png`、`landing-mobile.png`，
量 5 秒 FPS，並寫 `landing-report.json`。

## 模型檢視頁程式位置（`/viewer.html`）

- `src/pages/Viewer.vue`：掛載、卸載、載入與錯誤提示。
- `src/three/createRenderer.ts`：sRGB、ACES、DPR 上限 1.5。
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
陰影目前只在載入和調光後更新；之後加入物件動畫時，需重新啟用陰影更新。

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
截圖在 `test-results/`，供人工視覺審查；這不是正式 mobile fallback 或效能 audit。

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
GSAP 依 roadmap 安裝，這一步尚未使用，也不會打包進頁面。
目前主 JS 約 708 kB（gzip 約 188 kB），debug chunk 約 35.5 kB（gzip 約 10.1 kB）；
Vite 仍會提示主 chunk 超過 500 kB，
後續網站與效能階段再規劃載入策略。

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
