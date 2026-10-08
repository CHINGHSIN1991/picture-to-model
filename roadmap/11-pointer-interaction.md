# Step 11 — 加滑鼠互動

## 目標

模型**微妙地**跟著游標轉,有彈簧 / 阻尼感,離開時平滑回到中性。

## 為什麼

影片中的 asset 會跟著游標,是「活的」感覺的主要來源。
但要克制:太大的旋轉會破壞構圖,直接 snap 到座標會很廉價。

## 前置條件

- Step 10 完成

## 操作步驟

### 1. 要求 Codex 實作

```
Add subtle pointer interaction to the 3D asset.

Implement in web/src/three/InteractionController.ts.

Behavior:
- pointer movement slightly rotates the object
- movement should use spring/damping
- never directly snap to pointer coordinates
- maximum rotation should remain subtle
- return smoothly toward neutral when the pointer leaves

Do not interfere with scrolling.

Listen on window (not the canvas), since the canvas has pointer-events: none.
Expose maxRotation, stiffness, and damping as config values.
Respect prefers-reduced-motion: disable the effect when set.
```

### 2. 核心概念

正確:
```
mouse X
  ↓
targetRotationY
  ↓
lerp / spring
  ↓
model.rotation.y
```

錯誤:
```ts
model.rotation.y = mouseX;   // 不要這樣
```

### 3. 參考實作

```ts
export interface PointerConfig {
  maxRotationX: number;  // 弧度,建議 0.08
  maxRotationY: number;  // 弧度,建議 0.15
  damping: number;       // 0~1,建議 0.08
}

export class InteractionController {
  private target = { x: 0, y: 0 };
  private current = { x: 0, y: 0 };

  constructor(private cfg: PointerConfig) {
    window.addEventListener('pointermove', this.onMove);
    window.addEventListener('pointerleave', this.onLeave);
  }

  private onMove = (e: PointerEvent) => {
    const nx = (e.clientX / window.innerWidth) * 2 - 1;   // -1..1
    const ny = (e.clientY / window.innerHeight) * 2 - 1;
    this.target.y = nx * this.cfg.maxRotationY;
    this.target.x = ny * this.cfg.maxRotationX;
  };

  private onLeave = () => { this.target.x = 0; this.target.y = 0; };

  /** 每 frame 呼叫,回傳要「加」在 scroll 狀態上的偏移 */
  update() {
    this.current.x += (this.target.x - this.current.x) * this.cfg.damping;
    this.current.y += (this.target.y - this.current.y) * this.cfg.damping;
    return this.current;
  }

  dispose() {
    window.removeEventListener('pointermove', this.onMove);
    window.removeEventListener('pointerleave', this.onLeave);
  }
}
```

### 4. 與 scroll 狀態的疊加

重要:滑鼠偏移是**加在** scroll 決定的基礎旋轉上,不是取代。

```ts
// render loop
const p = interaction.update();
model.rotation.x = scrollState.rotation.x + p.x;
model.rotation.y = scrollState.rotation.y + p.y;
```

### 5. 觸控裝置

- 手機通常直接走 Step 14 的靜態 fallback。
- 若平板要保留 3D,可改用 `deviceorientation`(需 permission),或乾脆關閉。

## 完成條件 (Definition of Done)

- [ ] 游標移動時模型微轉,有阻尼感
- [ ] 游標離開視窗時平滑回正
- [ ] 旋轉幅度不破壞 hero 構圖
- [ ] scroll 不受影響
- [ ] `prefers-reduced-motion` 時無效果
- [ ] 參數在 config 中可調

## 下一步

→ [12-scroll-storytelling.md](./12-scroll-storytelling.md)
