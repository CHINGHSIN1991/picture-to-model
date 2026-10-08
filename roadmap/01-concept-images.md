# Step 01 — 先做概念圖,不要先建模

## 目標

用影像生成(影片中是 Astra)產出**多張** concept image,
從中找到主體輪廓、色彩、材質、比例、構圖,以及「哪個部分未來要動」。

## 為什麼

這是影片最重要的一個觀念:
**作者不是直接叫 AI 在 Blender 裡想設計,而是先產出多張概念圖,再挑一張當 3D reference。**

直接在 Blender 裡建模會遇到:
- AI 每次「想像」的東西不一樣,無法收斂
- 建模成本高,換方向代價大
- 沒有視覺目標,後面的 render 比對無從比起

概念圖便宜、快、可以大量嘗試。
影片中作者就是先試了 robot face、arm、hand 等方向,最後才選 infinity sculpture。

## 前置條件

- Step 00 完成
- 已決定主題(例如:「潛水員 + 錐狀珊瑚礁」)

## 操作步驟

### 1. 建立 references 目錄

```
references/
  concept-01.png
  concept-02.png
  concept-03.png
  concept-04.png
  concept-05.png
  concept-06.png
```

### 2. 生成概念圖

以「潛水員 + 錐狀珊瑚礁」為例,給影像生成模型的 prompt:

```
Create a gallery of six visual concepts for a premium interactive 3D website hero.

The central object should be a cone-shaped coral reef structure,
covered with detailed tropical coral formations.

A scuba diver should be floating beside or above it,
with schools of small fish surrounding the scene.

Requirements:
- premium product-design aesthetic
- strong silhouette
- suitable for conversion into a real-time WebGL / Three.js asset
- avoid overly fine geometry
- visually interesting from multiple angles
- cinematic lighting
- dark ocean background
- high contrast
- one main hero object

Generate multiple compositions and shape variations.
```

### 3. 評估每張概念圖

**這一步的目標不是最後圖片**,而是找到:

| 評估項目 | 要問的問題 |
|----------|-----------|
| 主體輪廓 | 縮小成 64px 還認得出來嗎?從側面、上面看還有特色嗎? |
| 色彩 | 主色、強調色是什麼?能在 WebGL 裡用簡單材質做出來嗎? |
| 材質 | 是硬面、有機、發光、透明?哪些可以用 texture 做,哪些需要 geometry? |
| 比例 | 主體與配角(潛水員、魚)的比例合理嗎? |
| 構圖 | 適合當 hero 嗎?留白夠放文字嗎? |
| 哪個部分未來要動 | 哪些元素可以拆開、旋轉、散開、重組?(對應 Step 12、13) |

### 4. 迭代

如果六張都不滿意,**改方向重做**,不要勉強用。
可以針對特定方向再生成:

```
Based on concept-03, generate four variations that:
- make the cone silhouette taller and more dramatic
- increase the amount of branching coral on the upper third
- move the diver to the upper-left so the right side has room for text
- keep the dark ocean background and high contrast
```

## 重要提醒

- **避免過細幾何**:概念圖裡太多細節,到 Blender 階段會變成 polygon 災難。
- **單一 hero object**:一張圖一個主角,方便後面做 scroll 動畫。
- **多角度有趣**:網站裡模型會旋轉,只有正面好看不夠。
- **先想動畫**:現在就標記「這個部分之後要散開」,Step 13 會需要。

## 完成條件 (Definition of Done)

- [ ] `references/` 內至少有 3~6 張概念圖
- [ ] 每張圖都做過上表的評估
- [ ] 已經知道「哪些部分未來要動」
- [ ] 心中有 1~2 張候選

## 下一步

→ [02-pick-reference-and-analyze.md](./02-pick-reference-and-analyze.md)
