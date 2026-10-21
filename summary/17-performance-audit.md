# Step 17 紀錄 — 效能 Audit

對應 roadmap：[roadmap/17-performance-audit.md](../roadmap/17-performance-audit.md)

狀態：已有分階段量測，尚未正式整體驗收；現況盤點日期 2026-10-21。

## 代表結果

| 已有證據 | 結果 | 來源 |
|---|---|---|
| GLB | 625,268 bytes、49,420 triangles、內嵌 64×64 色票 | [Step 06](06-export-glb.md) |
| Instancing 前後 | 固定視角含陰影 draw calls 182 → 56，面數不變 | [Step 13](13-decomposable-model.md) |
| 完整往返捲動 | M4 / Metal、1440×900、DPR 1.5，5 秒約 60 FPS、p95 16.8 ms | [scroll-report.json](../web/screenshots/scroll-report.json) |
| 手機 static | 零 3D 請求，約 219 KB；同條件 live 約 1000 KB | [Step 14](14-mobile-fallback.md) |
| 離屏與背景分頁 | 實際 Chrome trace：各一秒取樣零繪製、零 Three.js rAF 回呼，水光時間停止 | [Step 15](15-offscreen-pause.md) |
| DPR 上限 | 共用 config；兩入口 DPR 2 / 3 皆限制 1.5，連續 DPR 變更與 resize 驗證通過 | [Step 16](16-dpr-limit.md) |
| 回歸驗證 | Step 16 完成時 build 與 25 項瀏覽器測試通過 | [Step 16](16-dpr-limit.md) |

以上是既有紀錄，不是本次重新量測；也不是 Lighthouse 分數或手機效能結論。

## 這一步做了什麼

本次整理可供最終 audit 引用的資料，並列出尚未驗收的項目。
Step 14–16 已有靜態下載、可見性與 DPR 證據；`web/PERFORMANCE.md` 尚未建立，整體效能尚待驗收。

## 產出

已有：[export/REPORT.md](../export/REPORT.md)、[lighting-report.json](../web/screenshots/lighting-report.json)、
[pointer-report.json](../web/screenshots/pointer-report.json)、[scroll-report.json](../web/screenshots/scroll-report.json)、
[fallback-report.json](../web/screenshots/fallback-report.json)、[visibility-report.json](../web/screenshots/visibility-report.json)、
[resolution-report.json](../web/screenshots/resolution-report.json)。
待產出：完整 `web/PERFORMANCE.md`、Lighthouse mobile 報告，以及相同條件下的優化前後比較。

## 技術說明

待完成與驗證：

- 將 Step 14–16 的下載、暫停與 DPR 證據整合進最終報告。
- 在 production build 量測 GLB、圖片、JS 的下載與壓縮大小；統計 runtime 材質、貼圖與渲染負擔。
- 量測 Lighthouse mobile、LCP、CLS，記錄版本、節流與測試條件。
- 對照 mockup，確認優化沒有改變構圖或材質；達標或未達標都須列出原因。

roadmap 的 draw calls 目標為小於 50；目前固定視角含陰影是 56，尚不能宣告達標。
報告需註明是否含 shadow pass，不能拿單一 pass 的數字與整幀統計混比。
M4 的短時間 60 FPS 也不能代表低階手機；既有 build 仍有共用 chunk 大於 500 kB 的提示。

## Takeaway

- Step 14–16 已完成，分階段量測可作 baseline；完整效能結論仍需正式 audit。
- 最終完成狀態以明確的報告與測試證據更新，不以桌機看起來流暢代替。
