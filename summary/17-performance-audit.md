# Step 17 紀錄 — 效能 Audit

對應 roadmap：[roadmap/17-performance-audit.md](../roadmap/17-performance-audit.md)

狀態：完成，2026-10-21。動態含陰影 draw calls 高於 50，已在報告列出原因；不宣稱所有數值都達標。

驗證：TypeScript / production build、全部 26 項 Playwright 測試與量測腳本斷言通過。

## 代表結果

![Mockup、優化前與優化後](assets/17-performance-audit.png)

| 本次前後比較 | Before | After |
|---|---:|---:|
| Lighthouse mobile（三次皆） | 100 | 100 |
| LCP 中位數 / CLS | 1.579 s / 0 | 1.579 s / 0 |
| 手機 static 首次下載 | 225,630 B | 151,547 B（−32.8%） |
| 桌機 live 首次下載 | 1,026,263 B | 1,089,508 B（+63 KB） |
| 概念圖 | 155,820 B JPEG | 79,252 B WebP |
| 桌機捲動平均 FPS | 60.00 | 60.00 |
| 靜止／動態含陰影 draw calls | 29 / 56 | 29 / 56 |
| 固定 Hero 前後平均 RGB 誤差 | — | 0 / 255 |

## 這一步做了什麼

以 Step 16 build 保存基準，再對同一 production preview 條件量測下載量、GPU draw calls、面數、FPS 與 Lighthouse。
三次 Lighthouse 依序執行，使用中位數；原始報告、browser 版本、節流與資產 hashes 全數保留。
首次有另一個 Chrome 編碼程序重疊的預備量測整組排除並另外保存，沒有挑選單次最高分。

兩項實際調整：

- 概念圖改為同尺寸 WebP，quality 0.85，保留原 JPEG 供重編碼；加入 lazy loading、async decoding 與既有明確寬高。
- Live 載入時顯示既有 Hero WebP；Scene 畫完第一幀才回報 ready，再以 200 ms 淡出。減少動態效果時不淡出；載入失敗時保留圖與錯誤提示。

漸進載入新增桌機 Hero 圖片下載，抵銷圖片壓縮收益後 live 總量增加約 63 KB。
這是避免等待 GLB 時只有背景的取捨；手機 static 的總量則下降約 74 KB。
沒有修改 GLB、模型外觀、光源、陰影解析度或零件動畫。

## 產出

- [web/PERFORMANCE.md](../web/PERFORMANCE.md)：完整 before / after、所有 roadmap 目標逐項對照、瓶頸與量測限制。
- [Before 資料](../web/reports/performance/before/performance.json) · [After 資料](../web/reports/performance/after/performance.json)。
- [Before Lighthouse](../web/reports/performance/before/lighthouse-summary.json) · [After Lighthouse](../web/reports/performance/after/lighthouse-summary.json)：各三次原始 JSON 與壓縮 HTML 在相同目錄。
- [Runtime 資源](../web/reports/performance/after/resources.json)：2 個模型材質、3 個 scene mesh 材質、64×64 色票、384×512 environment atlas、2048×2048 shadow map。
- [視覺比較](../web/reports/performance/visual-comparison.png) · [漸進載入畫面](../web/reports/performance/after/progressive-loading.png) · [像素比較](../web/reports/performance/after/visual.json)。
- [audit-performance.mjs](../web/scripts/audit-performance.mjs)、[audit-lighthouse.mjs](../web/scripts/audit-lighthouse.mjs)、[audit-visual.mjs](../web/scripts/audit-visual.mjs)。
- [encode-concept.mjs](../web/scripts/encode-concept.mjs)：重編碼來源圖。

```bash
cd web
bun run build
bun run preview --port 4180 --strictPort
# 另一個終端機，避免量測彼此重疊
bun run audit:performance after
bun run audit:lighthouse after
# audit:visual 另需 5177 的 dev server；詳見 PERFORMANCE.md
bun run audit:visual
PLAYWRIGHT_CHANNEL=chrome bun run test
```

## 技術說明

本機條件是 Chrome 155、Apple M4 / ANGLE Metal、1440×900 CSS、renderer DPR 1.5；兩組 5 秒量測分別為靜止 Hero 與完整往返捲動加 pointer。
Lighthouse 13.5.0 使用預設 mobile 模擬、CPU 4× slowdown、三次獨立執行；它驗收的是手機 static 頁面。
正式 production 手機與 reduced-motion context 都沒有 Three / GSAP / GLB 請求。
Step 15 的真實切頁 trace 與 Step 16 的 DPR 證據整合進總報告，本次回歸再覆蓋相關生命週期。

GLB 維持 625,268 bytes、49,420 triangles；加上背景與動態陰影時最高每幀 98,074 triangles。
29 次主畫面繪製加 27 次 shadow pass 得到 56 calls，高於 roadmap 的 <50；保留陰影與零件控制，明確列為例外。
材質數由 traverse 計算，`renderer.info.memory` 僅用於 geometry / texture 計數，未把它當作材質數或 GPU 記憶體 bytes。

Vite 仍提示 625.69 KB Three 共用 chunk 超過 500 KB，但 static 模式不下載它。
部署端是否壓縮 GLB、實體低階平板表現與正式站點的長時間指標，未由本機模擬取代。
Hero 前後逐像素相同；原始 mockup 的 Blender 與既有網站 Three.js 光色差異如並排圖所示，並非本步造成。

## Takeaway

- 記錄實際下載與取捨，不能只列縮小的單一資產。
- 主 pass、shadow pass、幾何面數與每幀提交量要分開比較。
- Lighthouse 已達 100 時，下載下降不會再反映成更高分；仍應保留 before / after。
- Step 00–17 全部完成。正式部署與實體裝置驗收是後續獨立工作。
