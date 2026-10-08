# Step 14 — 做 Mobile Fallback

## 目標

桌機與夠強的裝置用活的 Three.js 場景;
小螢幕或效能受限的裝置改用**高品質靜態 WebP**,視覺上與 3D 初始構圖一致。

## 為什麼

影片特別強調這一點:作者就是用這種方法避免舊手機吃不消。

- 手機 GPU、記憶體、電池都有限
- 4~5 MB 的 GLB 在行動網路上下載很久
- 手機沒有滑鼠,Step 11 的互動本來就沒意義
- 一張 100~200 KB 的 WebP 就能給出 90% 的視覺效果

## 前置條件

- Step 10 完成(hero 已經能顯示)

## 操作步驟

### 1. 要求 Codex 實作

```
Implement a mobile fallback.

Desktop and sufficiently capable devices:
use the live Three.js scene.

Small screens or constrained devices:
replace the live scene with a high-quality still WebP.

The still image should visually match
the initial composition of the 3D scene.

Implement the decision in web/src/composables/useRenderMode.ts
returning 'live' | 'static'. Do not use only a width breakpoint.
Provide the still image as web/public/fallback/hero.webp (and a 2x variant),
and render it with <picture> + srcset in HeroSection.vue.
For scroll sections, provide one still per section state, or a single
hero still with CSS-only transforms as a simpler alternative.
```

### 2. 判斷條件(不要只看寬度)

不要只寫:

```ts
if (width < 768)   // 不夠
```

要綜合考慮:

```ts
export function decideRenderMode(): 'live' | 'static' {
  // 1. 使用者偏好
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return 'static';

  // 2. WebGL 能力
  const canvas = document.createElement('canvas');
  const gl = canvas.getContext('webgl2') ?? canvas.getContext('webgl');
  if (!gl) return 'static';

  // 3. 粗略硬體能力
  const cores = navigator.hardwareConcurrency ?? 2;
  const mem = (navigator as any).deviceMemory ?? 4;       // GB,Chrome only
  const dpr = window.devicePixelRatio ?? 1;
  const w = window.innerWidth;

  // 4. 螢幕尺寸 + 觸控
  const coarse = matchMedia('(pointer: coarse)').matches;

  // 5. 省流量
  const saveData = (navigator as any).connection?.saveData === true;

  if (saveData) return 'static';
  if (w < 768 && coarse) return 'static';
  if (cores <= 2 || mem <= 2) return 'static';
  if (w * dpr > 3000 && cores <= 4) return 'static';   // 高 DPR 小 GPU

  return 'live';
}
```

| 訊號 | 來源 | 用途 |
|------|------|------|
| 寬度 | `innerWidth` | 基本 |
| devicePixelRatio | `window.devicePixelRatio` | 高 DPR 代表 GPU 負擔大 |
| hardwareConcurrency | `navigator.hardwareConcurrency` | 核心數粗估 |
| deviceMemory | `navigator.deviceMemory` | 記憶體粗估(Chrome) |
| WebGL capabilities | `getContext('webgl2')`、`MAX_TEXTURE_SIZE` | 是否可渲染 |
| reduced-motion | `prefers-reduced-motion` | 使用者偏好 |
| pointer: coarse | media query | 是否觸控裝置 |
| saveData | `navigator.connection.saveData` | 省流量模式 |

### 3. 產生靜態圖

從 Three.js 場景直接截:

```ts
// 在桌機 viewer 中,用和 hero 相同的相機與光線
renderer.setPixelRatio(2);
renderer.render(scene, camera);
const url = renderer.domElement.toDataURL('image/png');
// 下載後用 cwebp / squoosh 轉 WebP,品質 80~85
```

或從 Blender render(Step 05 的 hero.png)轉 WebP。
**兩者擇一,但必須和 3D 初始構圖一致**,不然 fallback 看起來像另一個網站。

```bash
cwebp -q 82 hero@2x.png -o web/public/fallback/hero@2x.webp
cwebp -q 82 -resize 960 0 hero@2x.png -o web/public/fallback/hero.webp
```

### 4. 不要載入 GLB

`static` 模式下,**完全不要** import Three.js 與 GLB:

```ts
// useThreeScene.ts
if (mode === 'live') {
  const { createScene } = await import('../three/Scene');   // dynamic import
  ...
}
```

這樣 Three.js(~600 KB)與 GLB 都不會下載。

### 5. 驗證

- Chrome DevTools → Device toolbar → iPhone SE:看到 WebP,Network 裡沒有 `.glb`、沒有 three chunk
- 桌機:正常 3D
- 開啟 reduced-motion(macOS 系統設定):桌機也變靜態
- 桌機縮小視窗到 < 768:仍是 live(因為 pointer 不是 coarse)

## 完成條件 (Definition of Done)

- [ ] `useRenderMode.ts` 綜合多個訊號判斷
- [ ] 靜態 WebP 與 3D 初始構圖一致
- [ ] static 模式不下載 Three.js 與 GLB
- [ ] 手機模擬看到靜態圖,桌機看到 3D
- [ ] reduced-motion 生效

## 常見問題

- **靜態圖與 3D 顏色不一致** → 從同一個 renderer 截圖,而非 Blender render。
- **桌機縮小視窗變靜態** → 不要只看寬度,加 `pointer: coarse` 判斷。
- **iPad 判斷不準** → iPad 的 UA 像桌機;用 `maxTouchPoints > 1` 補判斷。

## 下一步

→ [15-offscreen-pause.md](./15-offscreen-pause.md)
