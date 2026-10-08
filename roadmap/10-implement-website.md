# Step 10 — 把 Mockup 做成真正網頁

## 目標

依 `mockups/final-homepage.png` 實作網站骨架,
使用 **Vue 3 + Vite + TypeScript + Three.js + GSAP**,
並把 Three.js 程式碼與 Vue UI 元件**分離**。

## 為什麼

- 影片 sample 用的是另一套結構;本專案照自己的 stack 走,不要照抄。
- Three.js 與 Vue 分離:3D 場景生命週期長、狀態複雜,塞進元件會很難維護,也不利於未來平台化(場景要能被外部 config 驅動)。
- 桌機 hero 必須是**活的** Three.js asset,不用預渲染影片。

## 前置條件

- Step 07 的 `web/` 專案存在
- Step 09 的 mockup 與 `SECTIONS.md`

## 操作步驟

### 1. 要求 Codex 實作

```
Implement the selected landing-page mockup (mockups/final-homepage.png).
Section-by-section 3D states are described in mockups/SECTIONS.md.

Stack:
- Vue 3
- Vite
- TypeScript
- Three.js
- GSAP + ScrollTrigger

Use the existing GLB asset at web/public/models/reef.glb.

Do not use pre-rendered video for the desktop hero.
The main object must remain a live Three.js asset.

Structure the Three.js code separately from the Vue UI components.
The Three.js scene should be a single persistent fixed canvas behind the page;
Vue sections scroll over it.

Reuse the lighting config from Step 08 (web/src/three/createLighting.ts).

For now:
- build all five sections with real layout and typography
- place the model in its Hero state only
- do NOT implement pointer or scroll interaction yet (next steps)
```

### 2. 目標結構

```
web/src/
├─ components/
│  ├─ HeroSection.vue
│  ├─ ReefSection.vue
│  ├─ EcosystemSection.vue
│  ├─ DivingSection.vue
│  └─ CTASection.vue
│
├─ three/
│  ├─ Scene.ts                 ← renderer / scene / camera / loop
│  ├─ ReefModel.ts             ← 載入 GLB、暴露可動 parts
│  ├─ createLighting.ts        ← Step 08
│  ├─ CameraController.ts      ← 相機狀態
│  ├─ InteractionController.ts ← Step 11
│  ├─ ScrollController.ts      ← Step 12
│  └─ config/
│     ├─ lighting.ts
│     ├─ materials.ts
│     └─ sections.ts           ← 對應 SECTIONS.md
│
├─ composables/
│  └─ useThreeScene.ts         ← Vue ↔ Three 的唯一橋接
│
├─ App.vue
└─ main.ts

web/public/models/reef.glb
```

### 3. 架構原則

| 原則 | 做法 |
|------|------|
| 單一 canvas | `position: fixed; inset: 0; z-index: 0`,所有 section `z-index: 1` 疊在上面 |
| Vue 不碰 Three 物件 | 只透過 `useThreeScene()` 回傳的 API(`setSectionState`, `setPointer`, `pause`, `resume`) |
| Three 不碰 DOM | 只接收 canvas element 與數值 |
| 所有狀態可序列化 | lighting / material / camera / sections 全部是 plain object |
| 清理 | `onUnmounted` 時 dispose renderer、geometry、texture |

### 4. ReefModel.ts 要暴露的介面

```ts
export interface ReefModel {
  root: THREE.Group;
  parts: Record<string, THREE.Object3D>;     // 依 MODEL_PLAN 名稱索引
  animatable: THREE.Object3D[];              // 可散開 / 重組的元件
  setMaterialParam(name: string, key: string, value: number | string): void;
}
```

### 5. 驗證

```bash
bun run dev
```

- 五個 section 都有版面與文字
- 模型在 Hero 狀態,位置與 mockup 一致
- scroll 時 canvas 固定、內容捲動
- 無 console error
- `bun run build` 成功

## 完成條件 (Definition of Done)

- [ ] 五個 section 元件存在,版面接近 mockup
- [ ] Three.js 程式碼全部在 `src/three/`,Vue 只透過 composable 存取
- [ ] 桌機 hero 是活的 Three.js 模型
- [ ] `bun run build` 通過
- [ ] 所有 config 是 plain object

## 常見問題

- **canvas 擋住點擊** → canvas `pointer-events: none`,互動在 Step 11 用 window 事件接。
- **元件 HMR 時場景重建** → 把 Scene 做成 module-level singleton,或在 composable 中快取。
- **字型 / 版面與 mockup 差很多** → 把 mockup 裁成每個 section 的小圖分別給 Codex。

## 下一步

→ [11-pointer-interaction.md](./11-pointer-interaction.md)
