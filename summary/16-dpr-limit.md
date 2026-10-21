# Step 16 紀錄 — DPR 上限

對應 roadmap：[roadmap/16-dpr-limit.md](../roadmap/16-dpr-limit.md)

狀態：部分實作，待集中設定與正式驗收；現況盤點日期 2026-10-21。

## 代表結果

以下限制已在 Step 07 起使用：

```ts
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
```

[Step 11 報告](../web/screenshots/pointer-report.json)記錄 CSS viewport 1440×900、canvas buffer 2160×1350。
另有 viewer 的 DPR 3 測試，預期 390×844 CSS viewport 對應 585×1266 buffer，證明高 DPR 也受 1.5 上限約束。

## 這一步做了什麼

本次補記前面已實作的限制，修正索引原先將本步一概列為「未開始」的狀態。
本次沒有修改 renderer，也未新增效能量測。

## 產出

| 既有檔案 | 已有內容 |
|---|---|
| [createRenderer.ts](../web/src/three/createRenderer.ts) | 初始化時限制 1.5，啟用 antialias |
| [Scene.ts](../web/src/three/Scene.ts) · [Viewer.ts](../web/src/three/Viewer.ts) | resize 時重新套用限制與尺寸 |
| [viewer.spec.ts](../web/tests/viewer.spec.ts) | 高 DPR 的 canvas buffer 驗證 |
| [pointer-report.json](../web/screenshots/pointer-report.json) | 桌機 CSS 與 buffer 尺寸紀錄 |

## 技術說明

尚缺 roadmap 要求的集中 config：目前 `1.5` 分別寫在 renderer 初始化、landing resize 與 viewer resize。
正式執行本步時，應整合為單一設定，並驗證兩個入口在 resize／DPR 改變後都遵守上限。
動態降低 DPR 是選配，尚未實作。

既有高 DPR 自動測試針對 viewer；landing 的量測紀錄不能取代完整的 DPR 變化回歸測試。

## Takeaway

- 數值限制已生效，但「值在 config 中」的完成條件尚未達成。
- 完成後將驗證條件與結果納入 [Step 17](17-performance-audit.md)。
