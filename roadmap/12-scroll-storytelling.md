# Step 12 — 加 Scroll Storytelling

## 目標

讓 3D 模型**跟著頁面一路走**:每個 section 有不同的位置、旋轉、縮放、拆解狀態,
用 GSAP ScrollTrigger 平滑插值。

## 為什麼

這是影片最有特色的部分:
3D sculpture 不只是 Hero 裝飾,而是貫穿整頁的敘事主角。

## 前置條件

- Step 10、11 完成
- `mockups/SECTIONS.md` 定義了每個 section 的模型狀態
- Step 13 的模型結構已確認可拆(如果需要「散開」效果,建議先看 Step 13)

## 操作步驟

### 1. 要求 Codex 實作

```
Create a scroll-driven narrative.

Implement in web/src/three/ScrollController.ts using GSAP ScrollTrigger.
Section states are defined in web/src/three/config/sections.ts
(derived from mockups/SECTIONS.md).

Section 1:
model centered and large.

Section 2:
model moves to the right and rotates 30 degrees.

Section 3:
selected components spread outward.

Section 4:
components slowly reassemble.

Section 5:
model moves left and settles into the CTA composition.

Use smooth interpolation.
Avoid abrupt transitions.

Use one ScrollTrigger per section with scrub: true,
tweening a plain state object (not Three.js objects directly).
The render loop reads that state object every frame.
Respect prefers-reduced-motion: jump between states instead of animating.
```

### 2. GSAP 控制的屬性

| 屬性 | 範例 |
|------|------|
| position | `model.position.x/y/z` |
| rotation | `model.rotation.y` |
| scale | `model.scale` |
| material | `emissiveIntensity`、`opacity` |
| individual mesh offsets | 每個 animatable part 的 local offset(散開 / 重組) |
| camera | `camera.position`、`fov` |

### 3. 狀態驅動的設計(重要)

**不要讓 GSAP 直接 tween Three.js 物件。** 改為 tween 一個 plain state:

```ts
// config/sections.ts
export interface SectionState {
  position: [number, number, number];
  rotation: [number, number, number];
  scale: number;
  explode: number;          // 0 = 組合, 1 = 完全散開
  emissive: number;
  cameraZ: number;
}

export const sections: SectionState[] = [
  { position: [0.6, 0, 0],  rotation: [0, 0, 0],    scale: 1.0, explode: 0, emissive: 1.0, cameraZ: 6 },
  { position: [1.8, 0, 0],  rotation: [0, 0.52, 0], scale: 0.8, explode: 0, emissive: 1.0, cameraZ: 6 },
  { position: [0, 0, 0],    rotation: [0, 1.57, 0], scale: 1.1, explode: 1, emissive: 1.6, cameraZ: 7 },
  { position: [0, 0, 0],    rotation: [0, 2.6, 0],  scale: 1.0, explode: 0, emissive: 1.2, cameraZ: 6 },
  { position: [-1.8, 0, 0], rotation: [0, 3.14, 0], scale: 0.7, explode: 0, emissive: 1.0, cameraZ: 6 },
];
```

```ts
// ScrollController.ts
const state = structuredClone(sections[0]);

sections.forEach((target, i) => {
  if (i === 0) return;
  gsap.to(state, {
    ...flatten(target),
    ease: 'none',
    scrollTrigger: {
      trigger: `#section-${i + 1}`,
      start: 'top bottom',
      end: 'top top',
      scrub: 1,
    },
  });
});

// render loop
model.position.set(...state.position);
model.rotation.y = state.rotation[1] + pointer.y;   // 疊加 Step 11
reefModel.setExplode(state.explode);
```

好處:
- 狀態可序列化 → 未來平台可以讓使用者編輯每個 section
- Three.js 物件只在 render loop 中被寫一次
- 容易 debug(印 state 即可)

### 4. 散開 / 重組(explode)

`ReefModel.setExplode(t)`:每個 animatable part 沿著「自身中心 → 模型中心」的方向偏移。

```ts
setExplode(t: number) {
  for (const part of this.animatable) {
    const dir = part.userData.explodeDir as THREE.Vector3;   // 載入時預先算好
    const dist = part.userData.explodeDist as number;
    part.position.copy(part.userData.restPosition).addScaledVector(dir, dist * t);
  }
}
```

細節見 Step 13。

### 5. 驗證

- 慢慢捲動,每個 section 的過渡平滑無跳動
- 快速捲動不會卡頓(scrub: 1 有緩衝)
- 捲回去狀態可逆
- `prefers-reduced-motion` 開啟時直接切換狀態

## 完成條件 (Definition of Done)

- [ ] `ScrollController.ts` 存在,用 state object 驅動
- [ ] `config/sections.ts` 與 `mockups/SECTIONS.md` 一致
- [ ] 五個 section 的過渡平滑
- [ ] 滑鼠偏移與 scroll 狀態正確疊加
- [ ] reduced-motion 行為正確

## 常見問題

- **section 切換時抖動** → 多個 ScrollTrigger 範圍重疊;確認 start/end 不重疊,或改用單一 timeline。
- **rotation 走最長路徑** → 弧度值累加而非跳躍(3.14 → 0 要寫成 6.28)。
- **ScrollTrigger 在 Vue 掛載前初始化** → 在 `onMounted` + `nextTick` 後再建立,並在 resize 後 `ScrollTrigger.refresh()`。

## 下一步

→ [13-decomposable-model.md](./13-decomposable-model.md)
