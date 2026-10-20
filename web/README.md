# Reef viewer — Step 07

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
- `src/three/createRenderer.ts`：sRGB、ACES、曝光、DPR 上限 1.5。
- `src/three/createScene.ts`：背景與基本三點光，包含一盞有陰影的主光。
- `src/three/loadModel.ts`：GLTFLoader、置中、console hierarchy、共享資源釋放。
- `src/three/Viewer.ts`：PerspectiveCamera、OrbitControls、尺寸調整、render lifecycle。

主視角取自 `blender/scripts/02_detail.py`，使用相同方位、仰角、鏡頭與 target；
以實際頂點計算窄螢幕所需相機距離，保留完整沙地和潛水員。
置中只移動 GLTFLoader 的包裝節點，GLB 內部零件的 pivots 與 local transforms 保留。

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
面數、滑鼠旋轉與縮放、響應式尺寸、DPR、模型 404、WebGL 不可用。
截圖在 `test-results/`，供人工視覺審查；這不是正式 mobile fallback 或效能 audit。

TypeScript 固定為 5.9.3，因為本次安裝的 TypeScript 7 與 vue-tsc 3.3.13 不相容。
GSAP 依 roadmap 安裝，這一步尚未使用，也不會打包進頁面。
目前 build 的 JS 約 698 kB（gzip 約 184 kB），Vite 會提示超過 500 kB；
後續網站與效能階段再規劃載入策略。

## 視覺基準

完成截圖見 [Step 07 總結](../summary/07-minimal-threejs-viewer.md)。
Blender 使用 AgX / Medium High Contrast，本頁依 roadmap 使用 ACES；
色彩與構圖接近，但即時 directional shadows 比 Blender area lights 更硬。
Step 08 再調整水下光線與材質氣氛。

參考：[Three.js OrbitControls](https://threejs.org/docs/pages/OrbitControls.html)、
[Vite](https://vite.dev/guide/)。
