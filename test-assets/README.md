# 測試素材記錄

目錄規範:`test-assets/<類型>/<物件名>/<視角>.png`

- 類型:`hard-surface`(硬表面)、`organic`(有機曲面)、`reflective`(透明/金屬/高反光)
- 視角命名:`front` / `back` / `left` / `right` / `side` / `top` / `perspective`;多視角合一的原始 sheet 保留為 `sheet.jpeg`
- 規格建議:白底或去背、正方形、≥1024px

## 素材清單

| 物件 | 類型 | 視角檔案 | 來源 / 備註 |
|---|---|---|---|
| coral-mound | organic | front(491)/ side(477)/ top(381) | 珊瑚礁小山三視圖(sheet 1408×768,AI 生成),2026-08-24。切圖後各視角僅 ~400-500px,低於建議 1024px;正式評估前建議以更高解析度重新輸出 |
| vintage-radio | hard-surface | front(655)/ back(560)/ side(365)/ top(655)/ perspective(655) | 復古金屬收音機五視圖(sheet 2816×1536,AI 生成),2026-08-24。金屬霧面材質,兼可觀察 metallic/roughness 判斷 |
| fishbowl | reflective | front(648)/ left(645)/ right(648)/ top(613)/ back(600) | 玻璃魚缸水族造景五視圖(sheet 2816×1536,AI 生成),2026-08-25。透明玻璃 + 反光 + 內部複雜結構,是最嚴苛的測試——切圖時已移除 sheet 上的文字標籤與地平線 |

## 待補

- [ ] coral-mound 高解析度版本
