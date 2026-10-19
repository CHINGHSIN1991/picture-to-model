# Step 01 總結 — 概念圖

對應 roadmap:[roadmap/01-concept-images.md](../roadmap/01-concept-images.md)
狀態:完成(2026-10-09)

## 這一步做了什麼

1. 定下主題:**潛水員 + 錐狀珊瑚礁,low-poly 玩具感**。
2. 在 [references/README.md](../references/README.md) 留下可重用的影像生成 prompt 範本與檔名規則。
3. 使用者自行提供一張概念圖(原檔 1448×1086 PNG),存為 `references/concept-01.png`。
4. 依 roadmap 的六個評估面向(輪廓、色彩、材質、比例、構圖、未來要動的部分)逐項評分,寫進 [references/evaluation.md](../references/evaluation.md)。
5. 列出「幾何複雜度警訊」:哪些元素照畫會變 polygon 災難,以及打算怎麼降階。

## 產出

| 檔案 | 內容 |
|---|---|
| `references/concept-01.png` | 唯一候選概念圖 |
| `references/evaluation.md` | 評分表、幾何警訊、候選、迭代紀錄 |
| `references/README.md` | prompt 範本、檔名規則、評估 checklist |

## 技術說明

評估結論直接決定了後面 Step 02–04 的建模策略:

| 評估面向 | 結論 | 對後續的影響 |
|---|---|---|
| 輪廓 | 藍色岩塊堆成寬底三角 / 錐狀,縮到 64px 仍可辨 | Step 03 的主山體就是「一個主峰 + 階梯狀收束」 |
| 色彩 | 全部是飽和平光單色,無漸層 | Step 04 決定用一張 64×64 色票貼圖取代所有材質 |
| 材質 | 全硬面 low-poly,無透明 / 發光 / 毛髮 | 一個 Principled BSDF、roughness 0.55、metallic 0 即可 |
| 比例 | 潛水員約礁石高度 1/3 | Step 03 的 `DIVER_LENGTH = 0.60 m`,礁石高 1.65 m |
| 構圖 | 主體在下半,上方留白 | hero 相機維持低仰角,留天空給網頁文字 |
| 要動的部分 | 岩塊、珊瑚、海草、魚、潛水員都是獨立零件 | 命名規則與 origin 規則在 Step 02 寫進 PROJECT_SPEC |

幾何警訊的處理方式(全部在 Step 04 兌現):

- 樹枝狀紅珊瑚 → 2 個 variant + linked duplicate。
- 腦珊瑚溝紋 → 不刻 geometry,用面片顏色變化暗示。
- 管狀珊瑚叢約 10 叢 → 2 個 variant、instancing。
- 海草擺動 → 留給 Three.js vertex shader,Blender 只給靜態 mesh。
- 氣泡、光束、焦散、沙地細石 → 全部不做 geometry。

## Takeaway

- **只生成一張就收斂是合理的**:這張圖本身就是 low-poly 風格,roadmap 列的四項選擇標準全部符合;再生成只會增加搖擺的機會。但這是例外,不是常態,README 的 prompt 範本仍保留「六張 gallery」的做法。
- **評估表的價值不在評分,而在「幾何警訊」那一節**。它把概念圖的每個元素預先分成 geometry / texture / 不做,後面 MODEL_PLAN 的 geometry-vs-material 表幾乎是直接搬過去。
- **「哪個部分未來要動」在這一步就要寫**。本專案因為提前標記,Step 02 才能把動畫 mode 與 origin 規則一次定好,Step 03–05 都沒有回頭改結構。
- 概念圖裡的氣泡與光束是氛圍,不是模型;把它們明確劃給 Web 階段,Blender 的 scope 才守得住。
