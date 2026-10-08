# Step 17 — 最後要求 AI 做效能 Audit

## 目標

系統性量測整個 3D 網站的下載量、渲染負擔、效能策略是否生效,
並**在不改變視覺設計的前提下**優化明顯問題。

## 為什麼

影片最後一步就是針對 hardware / mobile / download size 做檢查。
前面 Step 14~16 各自做了一項策略,這一步是整體驗收。

## 前置條件

- Step 10~16 完成

## 操作步驟

### 1. 要求 Codex 做 audit

```
Perform a performance audit of this 3D website.

Measure or inspect:

- GLB download size
- texture download size
- triangle count
- draw calls
- material count
- texture resolution
- renderer pixel ratio
- average desktop FPS
- likely mobile bottlenecks
- whether rendering pauses offscreen
- whether mobile fallback works
- reduced-motion behavior

Optimize obvious problems without materially
changing the visual design.

Write the report to web/PERFORMANCE.md with before/after numbers.
```

### 2. 量測方法

| 項目 | 怎麼量 | 目標 |
|------|--------|------|
| GLB 大小 | `ls -lh web/public/models/reef.glb` / Network panel | < 5 MB |
| Texture 大小 | gltf-validator 報告,或 Network 看 | 含在 GLB 內 |
| 三角面 | `renderer.info.render.triangles` | < 200k |
| Draw calls | `renderer.info.render.calls` | < 50 |
| Material 數 | `renderer.info.memory` + traverse 計數 | < 10 |
| Texture 解析度 | traverse material maps,印 `image.width` | ≤ 2048 |
| Pixel ratio | `renderer.getPixelRatio()` | ≤ 1.5 |
| 桌機 FPS | stats.js,或 Performance 面板 | 60 |
| JS bundle | `bun run build` 輸出 | three chunk 獨立、static 模式不載 |
| LCP / CLS | Lighthouse | LCP < 2.5s |
| Offscreen pause | Performance 面板捲到 footer | 無 rAF |
| Mobile fallback | Device toolbar | 無 .glb 請求 |
| reduced-motion | 系統設定開啟 | 靜態或直接切換 |

### 3. 加一個 debug overlay(可用 `?debug` 開)

```ts
import Stats from 'three/addons/libs/stats.module.js';
const stats = new Stats(); document.body.appendChild(stats.dom);

setInterval(() => {
  const r = renderer.info.render;
  console.table({ calls: r.calls, triangles: r.triangles, dpr: renderer.getPixelRatio() });
}, 2000);
```

### 4. 常見優化(由小到大)

| 問題 | 優化 | 影響視覺? |
|------|------|-----------|
| GLB 太大 | texture 降到 1024 / JPEG q80;Draco 壓 geometry | 幾乎不 |
| Draw calls 多 | InstancedMesh(Step 13);合併同材質 mesh | 不 |
| Material 多 | 合併到 texture atlas | 不 |
| FPS 低 | 降 DPR;關 bloom;降 shadow map;關 `antialias` 改 FXAA | 微小 |
| 載入慢 | `<link rel=preload>` GLB;先顯示 WebP 再換成 3D(漸進) | 不 |
| JS bundle 大 | Three.js tree-shake(只 import 需要的);dynamic import | 不 |
| 捲動卡頓 | ScrollTrigger `scrub: 1` 緩衝;避免在 scroll 中做 allocation | 不 |
| 記憶體 | dispose 未用的 geometry/texture;`renderer.info.memory` 監測 | 不 |

### 5. 漸進載入(推薦)

讓首屏先顯示 Step 14 的 WebP,GLB 載完再 crossfade 到 3D:

```
0ms:    HTML + CSS + WebP(~150KB)→ 使用者看到完整 hero
~1.5s:  Three.js chunk 載完
~3s:    GLB 載完 → fade in canvas, fade out WebP
```

LCP 由 WebP 決定,3D 是加分。

### 6. 報告格式

`web/PERFORMANCE.md`:

```markdown
# Performance Audit — 2026-xx-xx

## Download
| Asset | Before | After |
|-------|--------|-------|
| reef.glb | 6.8 MB | 3.9 MB |
| three chunk | 640 KB | 520 KB |
| hero.webp | — | 142 KB |

## Render (desktop, 1440×900, DPR 1.5)
| Metric | Before | After |
|--------|--------|-------|
| Triangles | 184k | 184k |
| Draw calls | 112 | 23 |
| FPS | 48 | 60 |

## Strategies
- [x] Offscreen pause
- [x] Mobile fallback (no GLB on mobile)
- [x] reduced-motion
- [x] DPR ≤ 1.5
- [x] Progressive load (WebP → 3D)

## Lighthouse (mobile)
- Performance: 94
- LCP: 1.8s
```

## 完成條件 (Definition of Done)

- [ ] `web/PERFORMANCE.md` 有 before/after 數字
- [ ] 所有「目標」欄位達標,或有說明為何不達標
- [ ] 視覺與 mockup 無明顯差異(並排截圖)
- [ ] Lighthouse mobile performance ≥ 90

## 完成!

→ 回到 [README.md](./README.md) 或看 [pipeline-overview.md](./pipeline-overview.md)
