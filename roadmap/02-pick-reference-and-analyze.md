# Step 02 — 挑一張概念圖當唯一 reference,並做建模分析

## 目標

1. 從概念圖中選定**唯一一張**作為 `references/final-concept.png`。
2. 讓 Codex 在動手建模前,先**分析**這張圖該怎麼轉成 web 3D asset。
3. 從這一步開始,**收斂 AI 的自由發揮**。

## 為什麼

- 一張 reference 就是後面所有 render 比對的唯一標準。多張會讓 AI 來回搖擺。
- 先分析再建模,可以提前決定「哪些是 geometry、哪些用材質做」,避免 polygon 爆炸。
- 提前規劃「哪些要分開」,後面 scroll / 拆解動畫才做得出來。
- Blender Agent Studio 本身也建議:先灰模、確認比例,再投入材質與細節。

## 前置條件

- Step 01 完成,有候選概念圖

## 操作步驟

### 1. 選定 reference

```
references/
  final-concept.png   ← 唯一的 reference
```

選擇標準(優先順序):
1. 輪廓強、多角度都有特色
2. 幾何複雜度可控(細節多但可以用材質/texture 表現)
3. 可拆解的元件明確
4. 適合網站構圖(有留白)

### 2. 要求 Codex 做建模分析(還不要建模)

```
Use references/final-concept.png as the primary visual reference.

I want to turn this design into a real-time web 3D asset.

Before modeling:
1. analyze the major forms
2. identify which parts should be actual geometry
3. identify which details should use materials or textures
4. keep the topology appropriate for a Three.js website
5. avoid unnecessary geometry
6. plan how the object can later be animated interactively

Also use the installed Blender Agent Studio modeling,
rendering and asset-validation skills when we reach the Blender stage.

Do not build the final detailed model immediately.
Start with a graybox.
```

### 3. 把分析結果存成文件

要求 Codex 把分析寫到 `blender/MODEL_PLAN.md`,內容至少包含:

```markdown
# Model Plan

## Major forms
- (主體 A:錐狀珊瑚礁本體 — 一個 cone 基底 + 多個分枝)
- (主體 B:潛水員 — 低模人形,獨立物件)
- (配角:魚群 — 單一低模魚 + instancing)

## Geometry vs. Material
| 元素 | 做法 | 理由 |
|------|------|------|
| 錐體本體 | geometry | 輪廓主體 |
| 分枝珊瑚 | 低模 geometry,重複使用 | 需要可拆解 |
| 珊瑚表面紋理 | normal map / roughness | 省 polygon |
| 魚群 | 單一 mesh + InstancedMesh | 數量多 |

## Object hierarchy (for Three.js)
- Reef_Root
  - Reef_Base
  - Coral_Branch_01 ... Coral_Branch_N  ← 可獨立動
  - Coral_Plate_01 ...
- Diver
- Fish_Instance

## Animation plan
- 哪些物件會旋轉 / 散開 / 重組
- 哪些物件需要獨立 origin

## Polygon budget
- 總目標:< 150k triangles
- 各部位預算
```

### 4. 人工檢查分析

確認:
- 「要動的部分」確實被列為獨立物件
- polygon 預算合理(桌機 hero 通常 50k~200k triangles)
- 沒有把應該用材質表現的細節列成 geometry

## 完成條件 (Definition of Done)

- [ ] `references/final-concept.png` 存在,且只有一張
- [ ] `blender/MODEL_PLAN.md` 存在,包含 forms / geometry vs material / hierarchy / animation plan / budget
- [ ] 人工確認過分析合理

## 常見問題

- **AI 想一步做完整模型** → 明確重申「Start with a graybox. Do not add materials yet.」
- **分析太抽象** → 要求它列出具體物件名稱與預估面數。

## 下一步

→ [03-graybox.md](./03-graybox.md)
