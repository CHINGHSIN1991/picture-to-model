# reef.glb — Step 06 完成（2026-10-20）

[GLB 檔案](reef.glb) · [匯出前後主視角](../blender/renders/export/hero_comparison.png) · [重新匯入六視角](../blender/renders/export/contact_sheet.png)

由通過 Step 05 的 `blender/scenes/02_detail.blend` 匯出，原始場景檔未修改。
比對圖左側為原場景，右側為全新 Blender 程序重新匯入 GLB 後、使用相同相機與燈光的渲染。

## Asset 數字

| 項目 | 結果 |
|---|---:|
| 檔案大小 | 625,268 bytes = 0.625268 MB（十進位；約 610.6 KiB） |
| 專案大小上限 | <1.5 MB，通過 |
| 場景 triangles（含所有 instance） | 49,420 |
| Unique triangles | 16,690 |
| glTF mesh 資料 | 26 |
| 網格 nodes | 91 |
| 全部 nodes | 95（另有 4 個 empty） |
| Materials | 1，`Reef_Palette` |
| Textures / images | 1 / 1，64×64 sRGB PNG，內嵌 |
| Roughness / metallic | 0.55 / 0 |
| Animations / armatures | 0 / 0 |
| Cameras / lights | 0 / 0 |
| Draco / 其他必要 extensions | 無 / 無 |
| 軸向與尺度 | glTF +Y up；1 單位 = 1 m |
| 實際頂點包圍尺寸 | Blender：X 4.5 × Y 3.6 × Z 2.242443 m；glTF 對應 X 4.5 × Y 2.242443 × Z 3.6 m |
| 外部資源依賴 | 無；單一 GLB 已包含幾何、材質與色票 |

## 匯出與互動結構

`blender/scripts/03_export.py` 只選取 `Scene_Root` 及其子物件，排除 Camera 與三盞 softbox；清理未使用的 mesh、material、image data blocks。
沒有未套用 modifier。原本正值且等比例的 placement transforms 保留在 node，保護根部／底部／胸口 pivots，並保留 linked mesh。
設定 +Y up、Apply Modifiers、UV、normals、materials、PNG；關閉動畫、相機、燈光、Draco 與 GPU-instancing extension。

```text
Scene_Root
├─ Sand
├─ Reef_Root
│  ├─ Rock_Peak_001 + Rock_Tier_001…006
│  ├─ Rock_Boulder_A/B_*
│  ├─ Coral_*
│  └─ Kelp_*
├─ Diver
│  ├─ Diver_Body
│  ├─ Diver_Tank
│  ├─ Diver_Mask
│  ├─ Diver_Fin_L
│  └─ Diver_Fin_R
└─ Fish_Root
   └─ Fish_A/B/C_*
```

完整 95-node 階層與每個 mesh 的 triangle 數：[hierarchy.txt](hierarchy.txt)。
所有名稱、父子關係與共享 mesh 分組均在重新匯入後比對通過；左右蛙鞋與其他可動元件仍是獨立 node。

## 驗證結果

| 檢查 | 結果 |
|---|---|
| Khronos glTF Validator `2.0.0-dev.3.10` | 0 errors、0 warnings、0 infos、0 hints；報告未截斷 |
| 獨立 Blender Agent Studio inspector | `hard_gate_pass: true`、`issues: []` |
| Fresh import | 另一個 Blender 5.2.0 LTS 程序；清空到 0 objects 後 import GLB |
| 幾何 | 場景／unique triangles 不變；雙向最近頂點距離最大約 2.39×10⁻⁷ m（門檻 10⁻⁵ m） |
| Transform / origin | World matrix 最大元素差約 3.58×10⁻⁷；95 個 node 全通過 |
| 材質與 UV | 材質指派、PaletteUV 色票座標、roughness、metallic、色票像素一致 |
| 渲染 | 六個全景＋三個潛水員近照都通過；最大平均 RGB 差 1.114×10⁻⁶（0–1 範圍） |
| 視覺審視 | 已開啟主視角左右比對、六視角總覽、角色近照；單峰輪廓、顏色、朝向與裝備未見可辨差異 |

GLB 重新匯入保留法線與 UV 接縫的拆分頂點，因此 inspector 量到 40,488 vertices、22,296 boundary/non-manifold edges；這與原始可編輯 mesh 的拓撲統計不同。
這些共址屬性接縫不代表匯出新增可見裂洞；頂點位置、三角面數與渲染已另行比對。
無退化面、無效頂點、零長度邊、孤立頂點、wire edges 或缺少材質的面。

共用 glTF mesh 會減少檔案內重複幾何，尚未自動變成 Three.js InstancedMesh。
未做 runtime batching 時，本模型約有 91 次網格繪製／pass 的上限估計；26 份 unique mesh 也不等於已達成 <25 draw calls 的 Web 目標。
後續 viewer／效能階段需安排 instancing 或 batching 並實測，這一步保留互動所需的獨立節點。

## 重跑與證據

從專案根目錄執行：

```bash
blender --background --factory-startup --threads 2 --python-exit-code 1 --python blender/scripts/03_export.py
npm ci --prefix tools/gltf
npm --prefix tools/gltf run validate
```

匯出腳本會檢查 Step 05 通過紀錄與 `.blend` SHA-256，再匯出、啟動獨立程序驗證與渲染。
validator 依賴版本及 integrity 固定於 `tools/gltf/package-lock.json`；驗證本地檔案，不需上傳至外部 viewer。

- [asset_manifest.json](asset_manifest.json)：大小、面數、匯出選項、來源／腳本／GLB hashes。
- [roundtrip_checks.json](roundtrip_checks.json)：逐物件 matrix、雙向頂點距離、共用網格、材質與九張影像差異。
- [validator.json](validator.json)：官方格式驗證結果及對應 GLB hash。
- [metrics.json](metrics.json)：GLB 獨立 inspector；原始場景的獨立數據保留在 `blender/renders/final/metrics.json`。
- [visual_review.json](../blender/renders/export/visual_review.json)：實際開啟影像後的審視紀錄。

GLB 與渲染 PNG 依既有 `.gitignore` 規則排除於版本控制；腳本與報告保留，可重新產生。

## 完成條件

- [x] `export/reef.glb` 已產出，低於專案大小及面數預算。
- [x] `blender/scripts/03_export.py` 可重跑。
- [x] 全新程序重新匯入，幾何、材質、transform 與渲染比對通過。
- [x] glTF Validator 無 error。
- [x] 本報告包含完整 asset 數字與階層連結。
- [x] 可動元件保留為獨立 node。

下一步：Step 07，建立最小 Three.js viewer，實際在瀏覽器載入此 GLB。
