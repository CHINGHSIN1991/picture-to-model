# Step 15 — 3D 離開畫面就停止 Render

## 目標

canvas 不在 viewport 時暫停 render loop 與動畫,回到畫面時恢復。

## 為什麼

影片的重要效能策略:**不在 viewport → 暫停 render。**

不然網站從頭到尾一直:

```
60 FPS
60 FPS
60 FPS
60 FPS
```

即使使用者在看 footer 的純文字,GPU 也在燒。
筆電風扇、手機電池、其他分頁都會受影響。

## 前置條件

- Step 10 完成

## 操作步驟

### 1. 要求 Codex 實作

```
Use IntersectionObserver to pause the Three.js
render loop when the canvas is outside the viewport.

Resume rendering when it becomes visible again.

Also stop unnecessary animations while hidden.

Additionally:
- pause when document.visibilityState === 'hidden' (tab switched)
- render one final frame before pausing so the last state is correct
- when resuming, reset the delta-time clock to avoid a huge jump
- expose pause()/resume() on the Scene API so Vue can also control it
```

### 2. 概念

```ts
if (visible) {
  requestAnimationFrame(render);
}
```

而不是無條件一直 `requestAnimationFrame`。

### 3. 參考實作

```ts
// Scene.ts
private running = false;
private rafId = 0;
private clock = new THREE.Clock();

start() {
  if (this.running) return;
  this.running = true;
  this.clock.getDelta();            // 重置 delta,避免恢復時 dt 爆大
  this.loop();
}

stop() {
  this.running = false;
  cancelAnimationFrame(this.rafId);
  this.renderer.render(this.scene, this.camera);   // 最後一幀,保證畫面正確
}

private loop = () => {
  if (!this.running) return;
  const dt = this.clock.getDelta();
  this.update(dt);
  this.renderer.render(this.scene, this.camera);
  this.rafId = requestAnimationFrame(this.loop);
};
```

```ts
// 可見性
const io = new IntersectionObserver(
  ([entry]) => (entry.isIntersecting ? scene.start() : scene.stop()),
  { threshold: 0 },
);
io.observe(canvas);

document.addEventListener('visibilitychange', () => {
  document.visibilityState === 'visible' ? scene.start() : scene.stop();
});
```

### 4. 注意:fixed canvas 的情況

本專案的 canvas 是 `position: fixed` 鋪滿整頁(Step 10),所以它**永遠**在 viewport 內。
這時 IntersectionObserver 要觀察的不是 canvas,而是「**模型實際出現的區域**」:

- 觀察所有有 3D 內容的 section(Hero ~ CTA)
- 任一 section 可見 → start;全部不可見(例如捲到 footer)→ stop

```ts
const sections = document.querySelectorAll('[data-has-3d]');
const visible = new Set<Element>();
const io = new IntersectionObserver((entries) => {
  for (const e of entries) e.isIntersecting ? visible.add(e.target) : visible.delete(e.target);
  visible.size > 0 ? scene.start() : scene.stop();
});
sections.forEach((s) => io.observe(s));
```

### 5. GSAP 動畫也要暫停

ScrollTrigger 本身在 scroll 時才更新,沒問題。
但如果有獨立的 `gsap.ticker` 動畫(例如珊瑚脈衝),一起暫停:

```ts
stop() { ...; gsap.ticker.sleep?.() ?? gsap.globalTimeline.pause(); }
start() { ...; gsap.globalTimeline.resume(); }
```

### 6. 驗證

- Chrome DevTools → Performance → 捲到 footer,確認沒有持續的 rAF
- 切換分頁再切回,畫面正確且無跳動
- 捲回 hero,動畫正常恢復

## 完成條件 (Definition of Done)

- [ ] 模型不在畫面時 rAF 停止(Performance 面板確認)
- [ ] 分頁隱藏時停止
- [ ] 恢復時無 dt 爆衝、無畫面跳動
- [ ] Scene API 有 `pause()` / `resume()`

## 下一步

→ [16-dpr-limit.md](./16-dpr-limit.md)
