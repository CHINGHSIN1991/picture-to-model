# Step 16 — 限制 DPR(Device Pixel Ratio)

## 目標

把 renderer 的 pixel ratio 限制在合理上限(建議 1.5),避免高 DPR 螢幕讓 GPU 負擔暴增。

## 為什麼

影片流程裡雖未細講,但實作上非常重要。

Retina Mac 的例子:

```
CSS 尺寸:      1440 × 900
DPR:           2
實際 GPU 渲染: 2880 × 1800  (= 4 倍像素)
```

3D 成本直接暴增 4 倍。
限制到 1.5 → 2160 × 1350,像素量約為 2.25 倍,視覺上幾乎看不出差異,但效能差很多。

## 前置條件

- Step 07 以後任何時候(建議在 Step 07 就設,這裡是正式確認)

## 操作步驟

### 1. 設定

```ts
renderer.setPixelRatio(
  Math.min(window.devicePixelRatio, 1.5)
);
```

### 2. 放進 config,並依裝置調整

```ts
// config/renderer.ts
export const rendererConfig = {
  maxPixelRatio: 1.5,
  antialias: true,
  powerPreference: 'high-performance' as const,
};

// Scene.ts
const dpr = Math.min(window.devicePixelRatio, rendererConfig.maxPixelRatio);
renderer.setPixelRatio(dpr);
```

可以進一步:

| 情境 | maxPixelRatio |
|------|---------------|
| 桌機、獨顯 | 1.5~2 |
| 桌機、內顯 / 筆電 | 1.25~1.5 |
| 平板(若保留 live) | 1 |
| 開啟 post-processing(bloom) | 再降 0.25 |

### 3. resize 時重新套用

```ts
window.addEventListener('resize', () => {
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, rendererConfig.maxPixelRatio));
  renderer.setSize(window.innerWidth, window.innerHeight);
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  ScrollTrigger.refresh();
});
```

視窗在不同 DPR 螢幕間拖動時 `devicePixelRatio` 會變,所以 resize 要重設。

### 4. 動態降級(可選,進階)

監測 FPS,連續低於 45 就降 DPR:

```ts
let frames = 0, last = performance.now();
function sampleFps() {
  frames++;
  const now = performance.now();
  if (now - last >= 2000) {
    const fps = (frames * 1000) / (now - last);
    if (fps < 45 && currentDpr > 1) {
      currentDpr = Math.max(1, currentDpr - 0.25);
      renderer.setPixelRatio(currentDpr);
    }
    frames = 0; last = now;
  }
}
```

### 5. 與 post-processing 的關係

如果用 `EffectComposer` + bloom,composer 也要 `setPixelRatio`,
bloom pass 的解析度可以再低(例如 0.5×),因為它本來就是模糊效果。

### 6. 驗證

```ts
console.log(renderer.getPixelRatio(), renderer.domElement.width, renderer.domElement.height);
```

在 Retina Mac 上應看到 `1.5, 2160, 1350`(以 1440×900 為例)。

## 完成條件 (Definition of Done)

- [ ] `setPixelRatio` 有上限,值在 config 中
- [ ] resize 時重新套用
- [ ] Retina 上 canvas 實際像素 ≤ 1.5× CSS 尺寸
- [ ] (可選)FPS 動態降級

## 常見問題

- **設 1 之後邊緣鋸齒明顯** → 保留 1.25~1.5,或開 `antialias: true`(MSAA 在 1.5 以下成本可接受)。
- **文字 / UI 糊** → DPR 只影響 canvas,HTML 文字不受影響;若 canvas 裡有文字 texture 需另外處理。

## 下一步

→ [17-performance-audit.md](./17-performance-audit.md)
