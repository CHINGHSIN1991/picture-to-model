# Step 09 — 再開始設計網站(先做 Mockup 圖)

## 目標

用影像生成產出**整頁網站的 mockup 圖**,選定一張後才開始寫程式。

## 為什麼

影片裡另一個關鍵:**網頁也先設計成 image mockup,再寫程式。**
不是邊寫 CSS 邊想畫面。

好處:
- 快速嘗試多種版面與視覺語言
- 和 3D asset 的構圖一起規劃(模型在每個 section 的位置)
- 給 Codex 一個明確的視覺目標,減少來回

## 前置條件

- Step 08 完成,有一張瀏覽器端的模型截圖(`web/screenshots/lighting-v1.png`)

## 操作步驟

### 1. 建立 mockups 目錄

```
mockups/
  homepage-01.png
  homepage-02.png
  homepage-03.png
  final-homepage.png   ← 選定後
```

### 2. 生成 mockup

把 `web/screenshots/lighting-v1.png`(或 `references/final-concept.png`)當作附圖,prompt:

```
Design a premium landing page around this 3D coral reef asset.

Create a full-page vertical website concept.

Sections:
1. Hero
2. Explore the reef
3. Marine ecosystem
4. Diving experience
5. CTA

The 3D coral asset should visually travel through the page.

At some sections:
- move left/right
- rotate
- zoom
- separate selected elements
- reassemble

Use a dark ocean-inspired visual identity.
Keep typography minimal and premium.

Produce three distinct layout variations.
```

### 3. 評估 mockup

| 評估項 | 要問 |
|--------|------|
| 3D 動線 | 模型在每個 section 的位置是否合理?移動路徑是否連貫? |
| 文字空間 | 每個 section 文字和模型是否打架? |
| 視覺一致 | 色彩、字型與 3D asset 的光線氛圍一致? |
| 可實作性 | 有沒有需要大量額外 3D 元素的 section? |
| 手機 | 直式縮下來還成立嗎?(Step 14 fallback 會用到) |

### 4. 選定並標註

選一張存成 `mockups/final-homepage.png`,
並寫一份 `mockups/SECTIONS.md` 描述每個 section 的 3D 狀態:

```markdown
# Sections

| # | Section | 模型位置 | 旋轉 | 縮放 | 狀態 |
|---|---------|----------|------|------|------|
| 1 | Hero | 置中偏右 | 0° | 1.0 | 完整 |
| 2 | Explore | 右側 | +30° Y | 0.8 | 完整 |
| 3 | Ecosystem | 置中 | +90° Y | 1.1 | 分枝散開 |
| 4 | Diving | 置中 | +150° Y | 1.0 | 重新組合 |
| 5 | CTA | 左側 | +180° Y | 0.7 | 完整 |
```

這份表就是 Step 12 scroll 動畫的 spec。

## 完成條件 (Definition of Done)

- [ ] `mockups/` 有 3 張以上候選
- [ ] `mockups/final-homepage.png` 選定
- [ ] `mockups/SECTIONS.md` 描述每個 section 的模型狀態

## 下一步

→ [10-implement-website.md](./10-implement-website.md)
