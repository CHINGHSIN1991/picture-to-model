# Step 05 — Render 出來檢查、修正

## 目標

**不要看到 `.blend` 有產生就算完成。**
用多角度 render 和 reference 比對,找出並修掉所有明顯問題。

## 為什麼

AI 建模常見的錯誤只有「看」才抓得到:
浮空的幾何、翻掉的 normals、物件互穿、材質反應不對、某些角度輪廓崩掉。
這些問題到了 Three.js 只會更明顯,現在修最便宜。

## 前置條件

- Step 04 完成

## 操作步驟

### 1. 要求 Codex 視覺檢查

```
Inspect the finished Blender model visually.

Render it from:
- hero perspective
- front
- back
- left
- right
- top

Save renders to blender/renders/final/.

Compare it against references/final-concept.png.

Check:
- silhouette
- proportions
- material response
- missing geometry
- floating geometry
- bad normals
- intersections
- lighting readability

Fix obvious issues automatically.
Update blender/scripts/02_detail.py so the fixes are reproducible.
```

### 2. 人工比對

把六張 render 和 reference 並排看。用這張 checklist:

| 檢查項 | 怎麼看 | 常見問題 |
|--------|--------|----------|
| 輪廓 | 把圖縮小 / 瞇眼看 | 剪影和 reference 差太多 |
| 比例 | 量主體 vs 配角 | 細化過程中被改掉 |
| 材質 | 看高光、粗糙度 | 太塑膠、太光滑 |
| 缺少幾何 | 對照 reference 元素清單 | 漏掉某個元件 |
| 浮空幾何 | 看接縫處 | 分枝沒接到本體 |
| Normals | 開 face orientation(藍/紅) | 有紅色面 |
| 互穿 | 看交界處 | 物件穿過本體 |
| 光線可讀性 | 看暗部細節 | 暗部糊成一團 |

### 3. 描述差異,迭代修正

覺得不像,就**直接描述差異**。影片裡作者發現想要的黃色發光效果沒出來,就繼續要求修改。

範例:

```
The overall geometry is correct,
but the coral currently looks too smooth and artificial.

Make the silhouette more organic.

Add:
- branching coral
- plate coral
- small irregular formations

Do not significantly increase polygon count.

Preserve the current overall cone silhouette.
```

其他常用修正句:

```
The emissive coral tips are not visible in the render.
Increase emission strength and make sure the emissive color is saturated orange-yellow.
```

```
From the top view the reef looks perfectly symmetrical, which reads as artificial.
Introduce slight asymmetry by rotating and scaling 30% of the branch instances randomly (seeded).
```

```
The diver intersects the reef from the left view. Move the diver 0.4m outward along its local X axis.
```

### 4. 技術檢查(非視覺)

```
Run a technical check and report:
- objects with non-applied scale or rotation
- objects with flipped normals
- objects with more than 20k triangles
- materials not using Principled BSDF
- objects whose origin is far from their geometry center
- unused data blocks (meshes, materials, images)
```

## 迭代次數建議

通常 2~4 輪。如果超過 5 輪還不收斂,代表:
- reference 本身不適合(回 Step 02 換)
- 或問題該到 Three.js 再解(光線 / 顏色類問題先放到 Step 08)

## 完成條件 (Definition of Done)

- [ ] `blender/renders/final/` 有六張 render
- [ ] 視覺 checklist 全部通過
- [ ] 技術檢查無紅字
- [ ] 所有修正都已回寫到 `02_detail.py`,重跑可重現

## 下一步

→ [06-export-glb.md](./06-export-glb.md)
