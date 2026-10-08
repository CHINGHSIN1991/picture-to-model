# Step 06 — 把 Blender 模型準備成 Web Asset(GLB)

## 目標

把 `.blend` 乾淨地 export 成 `.glb`,並**驗證** geometry、materials、transforms 都正確保留。

## 為什麼

不要直接「把 Blender 搬進瀏覽器」。真正的路徑是:

```
.blend
  ↓
GLB / glTF
  ↓
Three.js
```

**重要觀念(來自 Blender-to-Web workflow):**
Blender 的 physics、hair、constraints、lighting **不會**自動變成網頁行為。
網頁端通常要自己重新實作 motion、lighting 與 interaction。
GLB 只帶:mesh、材質(PBR 參數)、物件階層、transforms、(可選)動畫 keyframes。

## 前置條件

- Step 05 完成,模型已通過視覺與技術檢查

## 操作步驟

### 1. 要求 Codex export

```
Prepare this Blender asset for Three.js.

Export a GLB version to export/reef.glb.

Before exporting:
- apply required transforms
- remove unused geometry
- remove hidden objects
- remove unused materials
- check normals
- check object origins
- check scale
- preserve object separation required for interaction

After exporting:
re-open or inspect the GLB and verify that geometry,
materials and transforms survived correctly.

Report:
- GLB file size
- triangle count
- number of meshes
- number of materials

Save the export logic as blender/scripts/03_export.py so it can be re-run.
```

### 2. Export 設定建議

| 設定 | 建議值 | 理由 |
|------|--------|------|
| Format | glb (binary) | 單一檔案 |
| +Y Up | on | Three.js 慣例 |
| Apply Modifiers | on | |
| Include | Selected / Visible only | 避免帶到輔助物件 |
| Materials | Export | |
| Images | Auto / JPEG for color, PNG for normal | 控制大小 |
| Compression | Draco(可選) | 大檔案才用,需在 Three.js 載 DracoLoader |
| Animation | 只在有 keyframe 動畫時 on | 網頁動畫通常用 GSAP 做 |

### 3. 驗證 GLB

兩種方式,建議都做:

**a. 用 Blender 重新 import 檢查**
```
Import export/reef.glb into a fresh Blender scene, render the hero angle,
and compare it side by side with blender/renders/final/hero.png.
Report any difference in geometry, material, or orientation.
```

**b. 用 gltf-validator / 線上 viewer**
```bash
# gltf-validator
bunx gltf-validator export/reef.glb

# 或丟到 https://gltf-viewer.donmccurdy.com/ 看
```

### 4. 記錄 asset 報告

把報告寫到 `export/REPORT.md`:

```markdown
# reef.glb

- File size: 4.2 MB
- Triangles: 118,340
- Meshes: 47
- Materials: 6
- Textures: 4 (2× 2048 color JPEG, 1× 2048 normal PNG, 1× 1024 emissive)
- Draco: no
- Animations: 0
- Object hierarchy: (貼上)
```

### 5. 大小預算參考

| 項目 | 桌機 hero 建議上限 |
|------|------------------|
| GLB 總大小 | < 5 MB(含 texture) |
| 三角面 | < 200k |
| Materials | < 10 |
| Textures | 每張 ≤ 2048,總數 ≤ 6 |
| Draw calls | < 50(instancing 後) |

超過就先在這一步壓:降 texture 解析度、合併材質、Draco。

## 完成條件 (Definition of Done)

- [ ] `export/reef.glb` 存在
- [ ] `blender/scripts/03_export.py` 存在且可重跑
- [ ] 重新 import 的 render 與原 render 一致
- [ ] gltf-validator 無 error
- [ ] `export/REPORT.md` 有完整數字
- [ ] 可動元件在 GLB 中仍是獨立 node(用 viewer 看 hierarchy)

## 常見問題

- **顏色變淡 / 變灰** → 通常是 color management 問題,到 Step 07 處理;確認 export 時 base color texture 是 sRGB。
- **物件位置跑掉** → transforms 沒 apply,或 parent 關係有問題。
- **材質全黑** → normal map 格式錯,或 emissive 沒帶出來。
- **檔案太大** → texture 太多或解析度太高,先壓 texture;geometry 大才用 Draco。

## 下一步

→ [07-minimal-threejs-viewer.md](./07-minimal-threejs-viewer.md)
