# Step 15 紀錄 — 離開畫面暫停 Render

對應 roadmap：[roadmap/15-offscreen-pause.md](../roadmap/15-offscreen-pause.md)

狀態：已有 API 基礎，可見性控制尚未實作；現況盤點日期 2026-10-21。

## 代表結果

[Scene.ts](../web/src/three/Scene.ts) 已提供下列行為：

```ts
pause() {
  paused = true
  renderer.setAnimationLoop(null)
  lastTime = undefined
}
```

`resume()` 可恢復 loop，`useThreeScene()` 也已提供這兩個方法。目前尚未自動依可見性呼叫。

## 這一步做了什麼

本次盤點既有生命週期 API。`InteractionController` 的 visibilitychange 只把游標目標歸零，
不會停止 Scene render loop，不能視為分頁隱藏暫停已完成。

## 產出

已有：[Scene.ts](../web/src/three/Scene.ts)、[useThreeScene.ts](../web/src/composables/useThreeScene.ts) 的 pause / resume。
尚無本步專用可見性控制器或 Performance trace。

## 技術說明

待完成與驗證：

- 用 IntersectionObserver 觀察實際有 3D 內容的區域；固定滿版 canvas 本身始終在 viewport，不能用它判斷模型是否需要繪製。
- 合併區域可見性與 document.visibilityState，避免分頁隱藏時被另一個事件誤恢復。
- 暫停前同步最後畫面，恢復時清除時間差，確認零件與水光不跳動。
- 清理 observer 與事件；只控制本場景的動畫，不影響其他頁面元件。
- 用 Performance 紀錄確認暫停期間沒有持續 render，並測試切換分頁與捲回可見區域。

目前 Hero 到 CTA 都有 3D，footer 位於 CTA 內；不能直接假設「看見 footer」就代表模型完全離開畫面。

## Takeaway

- 有 pause / resume API 只是前置基礎，還需要觸發條件與停止繪製的證據。
- 接續 [Step 16](16-dpr-limit.md) 的 DPR 正式確認。
