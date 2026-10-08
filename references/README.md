# references/ — 概念圖與最終 reference

對應 [roadmap/01-concept-images.md](../roadmap/01-concept-images.md) 與 [02-pick-reference-and-analyze.md](../roadmap/02-pick-reference-and-analyze.md)。

## 檔名規則

```
references/
  concept-01.png … concept-06.png   ← Step 01:影像生成模型產出的候選
  final-concept.png                 ← Step 02:唯一的 reference,之後所有 render 都跟它比
  evaluation.md                     ← Step 01:每張概念圖的評估紀錄
```

- 一律 PNG,建議 1024px 以上長邊。
- 迭代版本用 `concept-03b.png`、`concept-03c.png`,不要覆蓋原圖。
- `final-concept.png` 是複製,不是搬移;原 concept 檔保留。

## 生成 prompt 範本

把 `<THEME>` 換成主題描述(例如 `a cone-shaped coral reef structure with a scuba diver floating beside it`):

```
Create a gallery of six visual concepts for a premium interactive 3D website hero.

The central object should be <THEME>.

Requirements:
- premium product-design aesthetic
- strong silhouette
- suitable for conversion into a real-time WebGL / Three.js asset
- avoid overly fine geometry
- visually interesting from multiple angles
- cinematic lighting
- dark background
- high contrast
- one main hero object

Generate multiple compositions and shape variations.
```

針對某張再迭代:

```
Based on concept-NN, generate four variations that:
- <change 1>
- <change 2>
- keep the dark background and high contrast
```

## 評估

每張圖填進 [evaluation.md](evaluation.md)。重點不是「最好看」,而是:

1. 縮到 64px 還認得出輪廓嗎?側面、上面看還有特色嗎?
2. 主色、強調色能用簡單 PBR 材質做出來嗎?
3. 哪些細節可以用 texture,哪些非得用 geometry?
4. 主角與配角比例合理嗎?
5. 當 hero 時留白夠放文字嗎?
6. 哪些部分之後要動(拆開、旋轉、散開、重組)?→ Step 12、13 會用到

## 完成條件

- [ ] 3–6 張 `concept-*.png`
- [ ] `evaluation.md` 每張都填
- [ ] 已標出「未來要動的部分」
- [ ] 1–2 張候選 → 進 Step 02 選出 `final-concept.png`
