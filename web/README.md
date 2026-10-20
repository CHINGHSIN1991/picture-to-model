# Reef viewer — Step 07–08

只用來檢查 `export/reef.glb` 的 Vue 3 + Vite + TypeScript + Three.js 頁面。

```bash
cd web
bun install --frozen-lockfile
bun run dev
```

開啟終端機顯示的 localhost 網址。拖曳旋轉、滾輪縮放、右鍵平移；
觸控使用單指旋轉、雙指縮放／平移。

`dev` 與 `build` 都先將 `../export/reef.glb` 複製至 `public/models/reef.glb`。
如果來源不存在，先依 Step 06 重新匯出；模型副本、依賴與 build 產物不納入 Git。

## 程式位置

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

主視角取自 `blender/scripts/02_detail.py`，使用相同方位、仰角、鏡頭與 target；
以實際頂點計算窄螢幕所需相機距離，保留完整沙地和潛水員。
置中只移動 GLTFLoader 的包裝節點，GLB 內部零件的 pivots 與 local transforms 保留。

## 水下調光（Step 08）

一般預覽：`http://127.0.0.1:5173/`

調光面板：`http://127.0.0.1:5173/?debug`

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

測試會自行啟動 `127.0.0.1:4173`，檢查 GLB SHA-256、全部 node 名稱與父子關係、
面數、滑鼠旋轉與縮放、響應式尺寸、DPR、模型 404、WebGL 不可用，
以及調光面板、設定匯出／重設、減少動畫偏好、卸載清理，共七項測試。
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
