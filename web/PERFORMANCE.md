# Performance Audit — 2026-10-21

Step 17 完成。Lighthouse mobile 三次皆為 **100 分**，LCP 中位數 **1.579 秒**、CLS **0**；
手機首次下載由 **225,630 → 151,547 bytes（−32.8%）**。
桌機靜止及完整往返捲動皆約 **60 FPS**。動態陰影幀 **56 draw calls** 仍超出 roadmap 的 <50 目標，原因與保留取捨如下。

TypeScript / production build、全部 **26 項 Playwright 測試**、production 量測與視覺比對斷言通過。

## 條件與可重現性

- 基準：Step 16 revision `5a97163b191155de2d90192efbad18eb1a6f9dd5`；After 為本次 Step 17 工作樹。
- Chrome **155.0.8059.85**、Lighthouse **13.5.0**、Vite production preview：`http://127.0.0.1:4180`。
- 桌機：Apple M4 / ANGLE Metal，1440×900 CSS、裝置 DPR 2、renderer DPR 1.5，buffer 2160×1350。
- Render：暖機後各取樣 5 秒；一組停在 Hero，另一組完整往返捲動並移動 pointer。以 WebGL draw 方法記錄實際提交，包含 shadow pass；同時記錄 rAF 間隔。各採樣幀都有 draw，並非只量空轉 rAF。
- 下載：全新 browser context、無網路節流；`PerformanceResourceTiming.transferSize` 加 navigation，包含瀏覽器回報的 headers。JS / CSS 的 encodedBodySize 小於 decodedBodySize，preview 有傳輸壓縮；GLB 本次仍以原始大小下載。
- Lighthouse：獨立依序執行三次，預設 mobile 412×823、DPR 1.75，模擬 RTT 150 ms、throughput 1638.4 Kbps、CPU slowdown 4×。原始設定與 environment 保留在 JSON，取三次中位數。
- 沒有正式部署或實體低階手機量測；分數不代表所有網路、裝置或 CDN 的實際結果。

```bash
cd web
bun install --frozen-lockfile
bun run build
bun run preview --port 4180 --strictPort
# 另一個終端機；依序執行，避免 Chrome 工作互相干擾
bun run audit:performance after
bun run audit:lighthouse after
# 視覺與 runtime resource 檢查還需要 dev server
bun run dev --port 5177 --strictPort
# 另一個終端機
bun run audit:visual
PLAYWRIGHT_CHANNEL=chrome bun run test
```

`VIEWER_URL` 可改 production preview 位址；`DEV_URL` 可改視覺腳本的 dev server 位址。
`audit:lighthouse` 預設 macOS Chrome，可用 `CHROME_PATH` 覆寫；HTML 報告以 gzip 儲存，解壓即可開啟。
`before` 模式應對 Step 16 build 執行，勿用新版 build 覆寫基準；before / after 各檔案的 hashes 在 performance.json。

第一次基準量測與概念圖編碼的 Chrome 程序重疊，結果 84 / 100 / 100 分；因此排除整組，保留於
[preliminary-overlap/](reports/performance/preliminary-overlap/)，再於無並行瀏覽器負載時重跑三次。
以下只使用重跑的正式基準，不混合取最高分。

## Download：本次前後比較

以下 KB 採十進位；總下載取樣包含已進入瀏覽器 lazy-load 預取距離的概念圖。

| 資產／情境 | Before | After | 說明 |
|---|---:|---:|---|
| GLB | 625,268 B | 625,268 B | SHA-256 完全相同，未改幾何 |
| GLB 內嵌色票 PNG | 338 B | 338 B | 64×64，沒有獨立 texture 請求 |
| 概念圖 | 155,820 B JPEG | 79,252 B WebP | 原尺寸、quality 0.85，−49.1% |
| Three / framing chunk（原始） | 625,693 B | 625,693 B | 動態 chunk，static 不下載 |
| 桌機 live 的 JS body（傳輸壓縮後） | 238,967 B | 241,413 B | Vue Transition 增加少量程式碼 |
| 手機 static 的 JS body（傳輸壓縮後） | 31,368 B | 33,816 B | 沒有 Three / GSAP |
| 桌機 live 首次總下載 | 1,026,263 B | 1,089,508 B | +63,245 B，新增載入預覽圖 |
| 手機 static 首次總下載 | 225,630 B | 151,547 B | −74,083 B（−32.8%） |
| 桌機 reduced-motion 首次總下載 | 329,226 B | 255,143 B | −74,083 B（−22.5%） |

漸進載入的桌機 Hero 使用既有 `hero-landscape@2x.webp`，新增 **137,030 B** 圖片 body。
概念圖節省抵銷部分成本，所以 live 總量仍增加約 63 KB；換取 GLB／shader 尚未就緒時就有完整模型畫面。
它不是減少桌機總下載的優化。手機 static 已有相同策略，這次沒有新增 3D 請求。

概念圖加上 `loading="lazy"` 與 `decoding="async"`，保留明確寬高。瀏覽器可提前載入鄰近畫面的 lazy 圖片；
本次 Network 仍載入它，因此下載節省主要來自 WebP 編碼，不把 lazy 標記誤算為零下載。

[before 數據](reports/performance/before/performance.json) · [after 數據](reports/performance/after/performance.json)。
每份 inventory 另列 raw / gzip / Brotli bytes；gzip / Brotli 是本地壓縮估值，不能當成已部署的傳輸設定。
GLB 本地 gzip 約 265,851 B，但本次 preview 的 GLB 沒有套用；可作部署階段的壓縮候選。

## Render 與資源

| 指標 | Before | After | roadmap 驗收 |
|---|---:|---:|---|
| 模型幾何三角面 | 49,420 | 49,420 | <200k，通過 |
| Hero 每幀三角面（含背景） | 49,422 | 49,422 | 通過 |
| 捲動每幀三角面最高值（含陰影） | 98,074 | 98,074 | <200k，通過 |
| Hero 靜止 draw calls | 29 | 29 | <50，通過 |
| 捲動 draw calls 中位數／最高值 | 56 / 56 | 56 / 56 | **高於 <50，保留並說明** |
| Hero 平均 FPS / p95 interval | 60.00 / 16.8 ms | 60.00 / 16.8 ms | 本機達 60 FPS |
| 捲動平均 FPS / p95 interval | 60.00 / 16.8 ms | 60.00 / 16.7 ms | 本機達 60 FPS；差異屬取樣波動 |
| Renderer DPR | 1.5 | 1.5 | ≤1.5，通過 |

75 個重複件維持合為 12 個 InstancedMesh，模型可見繪製物件共 28。
靜止時是 28 模型 + 1 背景 = 29 calls；動態時另外刷新 27 個陰影繪製，因此是 56。
未為壓到 50 而刪除陰影、合併不同動畫零件或改寫既有 pivots。
現有 M4 量測達 60 FPS，但這不等於低階 live 平板也達標；後續若需改善，應針對實機先評估陰影更新頻率與成本。

資源計數使用與 landing 相同的 model／材質／instancing／lighting 初始化，在獨立 dev fixture 掛載並 render 後 traverse，
不是把 `renderer.info.memory` 誤當成材質數：

| 資源 | 結果 |
|---|---|
| GLB 材質 | 1 |
| Runtime 模型材質 | 2（一般／珊瑚發光） |
| Scene mesh 材質 | 3（加程序水下背景；不含 Three 內建 shadow override） |
| 模型 texture | 一張 64×64 色票，GLB 內嵌 |
| 生成的 environment atlas | 384×512，沒有網路下載 |
| Shadow map | 2048×2048，沒有網路下載 |
| Renderer memory snapshot | 27 geometries、5 textures、7 programs；這是物件計數，不是 GPU bytes |

材質 <10、貼圖最大維度 ≤2048 均通過。[Runtime 計數](reports/performance/after/resources.json)。

Vite 仍提示 625.69 KB 共用 chunk 超過 500 KB；它承載 Three.js 與共用 renderer，已由動態 import 隔離。
Production static 的網路紀錄驗證未請求 Scene、ScrollController、Three / framing 或 GLB，故保留這個提示，
沒有只為隱藏 warning 拆成更多仍須同時載入的碎片。GLB <5 MB、texture 內嵌、live / static 分流均通過。

## 策略驗證

| 策略 | 結果與證據 |
|---|---|
| Offscreen / hidden pause | Step 15 真正 Chrome 切頁 trace：兩種暫停區間都是零 Three rAF 回呼；本次回歸重驗交錯事件與清理。[trace 說明](../summary/15-offscreen-pause.md) |
| 固定 canvas 的觀察範圍 | 觀察有 3D 的六個 wrapper；CTA footer 仍有模型，不能在 footer 任意停畫。離屏測試使用額外純文字 fixture |
| 手機 fallback | 本次 production 手機 context：static，無 canvas，零 3D / GLB 請求 |
| Reduced motion | 本次 production 初始 reduce：static；回歸測試也驗證 live 執行中切換時取消停留、直接套狀態 |
| DPR cap | 1.5；Step 16 已驗證兩入口連續 DPR 及尺寸變更，本次測得 2160×1350 buffer |
| Progressive load | Live 載入時保留 WebP，Scene 完成第一幀才 ready，200 ms 淡出；reduce 時不做淡出動畫。GLB 失敗時保留圖與錯誤訊息 |
| Cleanup | 原有 resize / DPR / pointer / visibility / ScrollTrigger 與 renderer 清理維持；沒有新增計時輪詢 |

可能的手機瓶頸：手機 static 主要是圖片與 Vue 的解析；live 平板則仍需下載 Three + GSAP + GLB、編譯 shader、
初始化 PMREM 與 2048 shadow map。高 DPR 已受限，但觸控尺寸／硬體 heuristics 不能代替實機測試。
本次未加入解碼成本較高的 Draco、後處理、動態 DPR 或全域 GSAP 暫停。

## Lighthouse mobile

| 指標（三次中位數） | Before | After | 目標 |
|---|---:|---:|---|
| Performance | 100 | 100 | ≥90，通過 |
| LCP | 1.579 s | 1.579 s | <2.5 s，通過 |
| CLS | 0 | 0 | 無量測到位移 |
| TBT | 0 ms | 0 ms | 無量測到阻塞 |

Before 三次均 100，After 三次均 100；下載減量未讓已達滿分的 Lighthouse 再上升。
這裡驗收的是預設手機 static 頁面，不是強制 mobile WebGL 的分數。

[Before Lighthouse](reports/performance/before/lighthouse-summary.json) · [After Lighthouse](reports/performance/after/lighthouse-summary.json)。
同目錄包含三次原始 `.report.json` 與 `.report.html.gz`。

## 視覺與範圍

![Mockup、優化前與優化後](reports/performance/visual-comparison.png)

1440×900 的 Hero 前後比較：平均 RGB 誤差 **0 / 255**、超過 24 的像素比例 **0**。
比較時強制 live + reduced-motion 固定水光；這是 Hero 的精確比對，不能外推為整頁逐像素一致。
概念圖採有損 WebP，構圖與尺寸不變；保留原始 JPEG 供重編碼。
原始 mockup 使用 Blender render，與既有網站的 Three.js 光色本來不同；此次保留既有構圖、文字、模型與材質。

[載入中預覽](reports/performance/after/progressive-loading.png) · [第一幀完成](reports/performance/after/progressive-ready.png) ·
[整頁 Before](reports/performance/before/desktop-full.png) · [整頁 After](reports/performance/after/desktop-full.png) ·
[像素比較資料](reports/performance/after/visual.json)。

整體驗收完成，保留兩個明確限制：動態含陰影 draw calls 為 56；本報告未涵蓋真實低階裝置或正式部署的長時間指標。
