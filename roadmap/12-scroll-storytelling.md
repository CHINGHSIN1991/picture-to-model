# Step 12 — 加 Scroll Storytelling

## 目標

讓 3D 模型**跟著頁面一路走**:每個 section 有不同的位置、旋轉、縮放、零件狀態,
用 GSAP ScrollTrigger 平滑插值。

每個 section 的狀態來自 `mockups/SECTIONS.md`;零件怎麼動來自 `PROJECT_SPEC.md`(經 Step 13 的 `PartAnimator`)。
這一步**不決定**動畫內容,只負責把 scroll 位置翻譯成狀態。

## 為什麼

這是影片最有特色的部分:
3D sculpture 不只是 Hero 裝飾,而是貫穿整頁的敘事主角。

## 前置條件

- Step 10、11 完成
- `mockups/SECTIONS.md` 定義了每個 section 的模型狀態與零件狀態
- Step 13 的模型結構已確認可拆,且 `PartAnimator` 可用(若 section 有任何零件動畫,先做 Step 13)

## 操作步驟

### 1. 要求 Codex 實作

把 `<SECTIONS.md 內容>` 換成實際的表。

```
Create a scroll-driven narrative.

Implement in web/src/three/ScrollController.ts using GSAP ScrollTrigger.
Section states are defined in web/src/three/config/sections.ts,
derived 1:1 from mockups/SECTIONS.md:

<SECTIONS.md 內容>

Part-level animation (the `parts` field of each state) is NOT implemented here:
pass it to PartAnimator.setProgress() (Step 13), which reads the modes from
config/partAnimations.ts. Do not hard-code any particular effect.

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
| parts | 每個 part group 的 `t`(0 = rest,1 = 離開狀態;mode 由 PROJECT_SPEC 決定) |
| camera | `camera.position`、`fov` |

### 3. 狀態驅動的設計(重要)

**不要讓 GSAP 直接 tween Three.js 物件。** 改為 tween 一個 plain state:

```ts
// config/sections.ts
export interface SectionState {
  position: [number, number, number];
  rotation: [number, number, number];
  scale: number;
  parts: Record<string, number>;   // key = PROJECT_SPEC 的 part group 名稱,值 = departure 0~1
  emissive: number;
  cameraZ: number;
}

// 以下只是示意,實際值來自 mockups/SECTIONS.md;section 數量不固定
export const sections: SectionState[] = [
  { position: [0.6, 0, 0],  rotation: [0, 0, 0],    scale: 1.0, parts: { rocks: 0, corals: 0, diver: 1, fish: 1 }, emissive: 1.0, cameraZ: 6 },
  { position: [1.8, 0, 0],  rotation: [0, 0.52, 0], scale: 0.8, parts: { rocks: 0, corals: 0, diver: 0, fish: 1 }, emissive: 1.0, cameraZ: 6 },
  { position: [0, 0, 0],    rotation: [0, 1.57, 0], scale: 1.1, parts: { rocks: 0, corals: 0, diver: 0, fish: 0 }, emissive: 1.6, cameraZ: 7 },
  // ...
];
```

```ts
// ScrollController.ts
const state = structuredClone(sections[0]);

sections.forEach((target, i) => {
  if (i === 0) return;
  const st = {
    trigger: `#section-${i + 1}`,
    start: 'top bottom',
    end: 'top top',
    scrub: 1,
  };
  gsap.to(state,       { ...flatten(target, ['parts']), ease: 'none', scrollTrigger: st });
  gsap.to(state.parts, { ...target.parts,               ease: 'none', scrollTrigger: st });   // 巢狀物件另開一個 tween
});

// render loop
model.position.set(...state.position);
model.rotation.y = state.rotation[1] + pointer.y;   // 疊加 Step 11
partAnimator.setProgress(state.parts);              // Step 13;mode 由 config 決定
```

好處:
- 狀態可序列化 → 未來平台可以讓使用者編輯每個 section
- Three.js 物件只在 render loop 中被寫一次
- 容易 debug(印 state 即可)
- 換動畫方式不用動這一層:只改 `config/partAnimations.ts`

### 4. 零件狀態的語意

`parts` 的每個值都是 `t`(departure):**0 = GLB 原位,1 = 該 mode 的離開狀態**。

- 進場效果(堆起、長出、下潛、環繞進場)→ 從前一個 section 的 `1` 走到 `0`
- 散開效果 → 從 `0` 走到 `1`
- Hero 若要一開始就完整 → 全部 `0`;若要「載入時長出來」→ Hero 也寫 `0`,但載入時用 `gsap.from` 把 `parts` 從 1 tween 到 0(時間驅動,與 scroll 無關)

細節與 mode 目錄見 Step 13。

### 5. 驗證

- 慢慢捲動,每個 section 的過渡平滑無跳動
- 快速捲動不會卡頓(scrub: 1 有緩衝)
- 捲回去狀態可逆
- `prefers-reduced-motion` 開啟時直接切換狀態

## 完成條件 (Definition of Done)

- [ ] `ScrollController.ts` 存在,用 state object 驅動
- [ ] `config/sections.ts` 與 `mockups/SECTIONS.md` 一致(含 `parts`)
- [ ] 所有 section 的過渡平滑
- [ ] 滑鼠偏移與 scroll 狀態正確疊加
- [ ] reduced-motion 行為正確
- [ ] 這一層沒有任何寫死的零件效果(grep 不到 explode / grow 等字眼,只有 `parts`)

## 常見問題

- **section 切換時抖動** → 多個 ScrollTrigger 範圍重疊;確認 start/end 不重疊,或改用單一 timeline。
- **rotation 走最長路徑** → 弧度值累加而非跳躍(3.14 → 0 要寫成 6.28)。
- **ScrollTrigger 在 Vue 掛載前初始化** → 在 `onMounted` + `nextTick` 後再建立,並在 resize 後 `ScrollTrigger.refresh()`。
- **`parts` 沒動** → `gsap.to(state, ...)` 不會深層 tween 巢狀物件,`parts` 要另開一個 tween(見上)。

## 下一步

→ [13-decomposable-model.md](./13-decomposable-model.md)
