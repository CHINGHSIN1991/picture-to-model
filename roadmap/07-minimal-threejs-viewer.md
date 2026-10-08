# Step 07 — 先做一個最簡單的 Three.js Viewer

## 目標

一個**只做一件事**的頁面:載入 GLB,看它在瀏覽器裡長什麼樣。
不做網站、不做互動、不做 scroll。

## 為什麼

- 先不要一口氣做完整網站。先確認 asset 在瀏覽器裡的真實表現。
- 這一步會暴露所有 export / color management / scale 問題。
- 影片也是先把 asset 放進簡單的 Three.js hero 確認 browser 表現。

## 前置條件

- Step 06 完成,有驗證過的 `export/reef.glb`

## 操作步驟

### 1. 建立 web 專案

```bash
cd /Users/chinghsinc/Develop/blender-to-model
bun create vite web --template vue-ts
cd web
bun install
bun add three gsap
bun add -d @types/three
mkdir -p public/models
cp ../export/reef.glb public/models/reef.glb
```

### 2. 要求 Codex 建 viewer

```
Create a minimal Three.js page that loads the exported GLB.

Project: web/ (Vue 3 + Vite + TypeScript, already scaffolded).
Put all Three.js code in web/src/three/ and keep it independent from Vue components.
Create a single route/page web/src/pages/Viewer.vue that mounts the scene into a full-screen canvas.

Requirements:
- PerspectiveCamera
- WebGLRenderer
- correct color management
- physically reasonable lighting
- responsive sizing
- OrbitControls temporarily enabled for inspection
- model centered correctly
- camera framed to match the original concept image

The purpose of this page is only to validate
how the Blender asset looks in the browser.
```

### 3. 關鍵設定(確認 Codex 有做)

```ts
// color management
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;

// DPR 限制(詳見 Step 16)
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));

// 置中
const box = new THREE.Box3().setFromObject(model);
const center = box.getCenter(new THREE.Vector3());
model.position.sub(center);
```

### 4. 開瀏覽器看

```bash
bun run dev
```

對照 `references/final-concept.png` 和 `blender/renders/final/hero.png`:

| 檢查項 | 預期 |
|--------|------|
| 模型有載入 | 看得到 |
| 尺度 | 不會太小或撐爆畫面 |
| 方向 | Y up、正面朝相機 |
| 顏色 | 和 Blender render 接近(不會灰掉 / 過曝) |
| 材質 | metallic / roughness 有反應 |
| 發光 | emissive 看得到 |
| 物件階層 | console 印出 `model.traverse` 名稱,和 MODEL_PLAN 一致 |

### 5. 印出 hierarchy 以備後用

```ts
model.traverse((o) => {
  if ((o as THREE.Mesh).isMesh) console.log(o.name, (o as THREE.Mesh).geometry.attributes.position.count);
});
```

## 建議檔案結構(這一步只需要)

```
web/src/
├─ three/
│  ├─ createRenderer.ts
│  ├─ createScene.ts
│  ├─ loadModel.ts
│  └─ Viewer.ts          ← 把以上組起來
└─ pages/
   └─ Viewer.vue
```

## 完成條件 (Definition of Done)

- [ ] `bun run dev` 開得起來,看得到模型
- [ ] 顏色與 Blender render 接近
- [ ] 相機框位和 concept 構圖接近
- [ ] OrbitControls 可以轉,各角度正常
- [ ] console 印出的物件名稱與 MODEL_PLAN 一致

## 常見問題

- **全黑** → 沒有光,或 `outputColorSpace` 沒設。
- **太灰 / 洗白** → tone mapping 或 texture colorSpace 錯。
- **模型不在畫面中** → 沒有置中,或 Blender 原點離模型很遠。
- **很糊** → `setPixelRatio` 設成 1 以下。

## 下一步

→ [08-web-lighting.md](./08-web-lighting.md)
