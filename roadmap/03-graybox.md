# Step 03 — 先建 Graybox(灰模)

## 目標

讓 Codex 透過 Blender Agent Studio 在 Blender 裡建出**簡單幾何**的灰模,
確認輪廓、比例、尺度、物件結構都對,**再**進入細節。

## 為什麼

不要第一個 prompt 就「Make this perfect」。正確流程是:

```
concept
  ↓
graybox
  ↓
compare
  ↓
fix proportions
  ↓
detail
```

灰模階段修比例成本極低;等到有材質、細節再改,牽一髮動全身。
這也是 Blender Agent Studio 的標準流程。

## 前置條件

- Step 02 完成,有 `references/final-concept.png` 與 `blender/MODEL_PLAN.md`

## 操作步驟

### 1. 要求 Codex 建立 graybox

```
Create the graybox version in Blender.

Follow blender/MODEL_PLAN.md for object hierarchy and naming.

Requirements:
- match the overall silhouette and proportions of the reference
- use simple geometry
- establish the correct scale
- organize objects with meaningful names
- keep potentially animated components separated
- prepare the scene for later GLB export

Render:
- hero angle
- front
- left
- right
- back
- top

Compare the renders against the reference image
and correct major proportion problems before continuing.

Save:
- the .blend file to blender/scenes/01_graybox.blend
- the Python script used to generate it to blender/scripts/01_graybox.py
- renders to blender/renders/graybox/
```

### 2. 檢查 render

把 `blender/renders/graybox/` 的六張圖和 `references/final-concept.png` 並排看。

重點只看:
- **輪廓**:整體剪影像不像?
- **比例**:主體與配角的大小關係對不對?
- **尺度**:物件的 Blender 單位是否合理(建議主體約 1~3 公尺)?
- **物件分離**:要動的部分是不是獨立物件?

**不看**:材質、顏色、細節、光線。現在都不重要。

### 3. 修正比例

有問題就直接描述差異,例如:

```
Compared to the reference:
- the cone is too wide; reduce the base radius by ~25% and keep the height
- the diver is too large relative to the reef; scale to roughly 1/4 of the reef height
- the upper third of the cone should flare outward slightly
Re-render all six angles and update 01_graybox.py so the script reproduces the corrected version.
```

**重點:修正必須回寫到 `.py`**,不能只改 `.blend`。

### 4. 確認物件結構

要求 Codex 列出 scene outliner:

```
Print the full object hierarchy with object names, types, and approximate dimensions.
Confirm that every component listed in MODEL_PLAN.md as "animatable" is a separate object with its own origin.
```

## 為什麼一定要存 Python script

這是本專案平台的核心設計:

```
使用者:「珊瑚再多一點」
  ↓
AI 修改 Python
  ↓
重新生成 Blender
  ↓
重新 export GLB
  ↓
網頁自動 reload
```

只留 `.blend` 就是不可重現的黑盒子。
Blender Agent Studio 本身也是以「保留 .blend + Python source」作為核心設計。

### Python script 的要求

- 從空場景開始可以完整重建(`bpy.ops.wm.read_factory_settings(use_empty=True)`)
- 參數集中在最上方(尺寸、數量、seed)
- 物件命名與 MODEL_PLAN.md 一致
- 腳本末尾自動存檔與 render

可以要求 Codex:

```
Make 01_graybox.py fully reproducible:
- start from an empty scene
- expose key dimensions as named constants at the top
- running `blender --background --python blender/scripts/01_graybox.py`
  must regenerate the .blend and all six renders without manual steps
```

然後自己驗證一次:

```bash
blender --background --python blender/scripts/01_graybox.py
```

## 完成條件 (Definition of Done)

- [ ] `blender/scenes/01_graybox.blend` 存在
- [ ] `blender/scripts/01_graybox.py` 存在,且可以從零重現場景
- [ ] `blender/renders/graybox/` 有 hero / front / left / right / back / top 六張
- [ ] 輪廓與比例與 reference 相符(人工確認)
- [ ] 可動元件都是獨立物件、名稱有意義
- [ ] 尺度合理

## 常見問題

- **AI 偷加材質或細節** → 回絕,重申「graybox only, no materials, no subdivision」。
- **render 太暗看不清輪廓** → 要求用 matcap 或平均的三點光,graybox 階段不追求美。
- **比例一直修不對** → 把 reference 和 render 疊圖(半透明)給 AI 看,或直接給數字。

## 下一步

→ [04-detailed-model.md](./04-detailed-model.md)
