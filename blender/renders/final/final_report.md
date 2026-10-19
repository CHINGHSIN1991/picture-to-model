# Step 05 渲染檢查與修正完成 — 2026-10-19

[主視角](hero.png) · [六視角總覽](contact_sheet.png) · [修正前總覽](../../revisions/detail_before_step05/renders/contact_sheet.png)

本輪保留原本的單峰山體，修正珊瑚、海草的接合與穿插，以及沙地朝下的法線。
最終來源已從空場景重建，九張影像重新輸出；獨立 asset inspector 與專案技術檢查均通過。

## 實際修正

原本先放置配角、再細修岩面，而且管叢只用中央一點定位，導致部分管根跨出平台、部分管口被岩石遮住。
現在先完成岩面，再以每根管子的底圈量測支撐，整叢保留共用網格並調整位置／旋轉。
最弱支撐的管根淺埋 3 mm，所有管口至少高出當地岩面 4.5 cm。
另移開一叢黃色珊瑚與一株海草，排除相鄰裝飾的表面穿插；沙地明確指定朝上的面繞序。
修正已寫回 `02_detail.py` 與 `detail_geometry.py`，固定調整值集中於 `DECORATION_ADJUSTMENTS`。

## 視覺檢查

已開啟 hero、六視角總覽、左／右／後原尺寸影像及潛水員近照，並比對 `references/final-concept.png`。
總覽上排為 hero / front / left，下排為 right / back / top。

| 項目 | 結果與證據 |
|---|---|
| 輪廓 | 通過：仍是一個中央主峰、寬底及低坡腳；山體幾何未改動。 |
| 比例 | 通過：潛水員、魚、岩塊尺寸不變；珊瑚微調後仍服從主峰。 |
| 材質 | 通過：藍色切面、暖色珊瑚、綠色海草與淺沙可辨，無曝光過亮的白塊。 |
| 缺少幾何 | 通過：所有珊瑚類型、海草、魚與潛水員裝備保留，91 個網格物件未減少。 |
| 浮空 | 通過：檢查側／後視圖與 171 個根部單元，未再發現整根懸空的管狀珊瑚。斜坡邊緣允許部分根圈外伸。 |
| 法線 | 通過：沙地朝上；閉合零件無反向體積或相鄰面繞序不一致。 |
| 互穿 | 通過：盤珊瑚附近重疊已移開；珊瑚／海草物件間 BVH 表面相交配對為零。 |
| 光線可讀性 | 通過：相同三盞 area light 與曝光，六角度均能辨識山體切面和配角。 |

風格仍是專案指定的低模玩具感，並非逐像素重現概念圖；氣泡、焦散、光束及水下背景效果依計畫留給 Web 階段。
背面依單張概念圖推定，沒有可供精確比對的背面參考。

## 技術結果

| 檢查 | 修正前 | 最終 |
|---|---:|---:|
| 根部取樣未接觸的單元（>1 mm） | 36 | 0 / 171 |
| 管口未達岩面上方 4.5 cm 的單元 | 17 | 0 / 104 |
| 珊瑚／海草表面相交物件配對 | 11 | 0 |
| 場景 triangles | 49,420 | 49,420 |
| Unique triangles | 16,690 | 16,690 |
| 網格物件 / unique meshes | 91 / 26 | 91 / 26 |

- 無超過 20k triangles 的單一網格；場景 <100k、unique <40k，魚每 variant 164 triangles。
- 一個 Principled BSDF、一張已 packed 的 64×64 sRGB 色票，roughness 0.55、metallic 0；所有網格有 PaletteUV。
- 無退化面、無效頂點、零長度邊、孤立頂點或 wire edges。192 條開放邊全部是刻意開放的沙地外圈。
- 未使用的 mesh、material、image data blocks 均為零，無未套用的 modifier。
- 79 個物件保留正值、等比例的 placement transforms，供 linked instances 與 Diver 整體尺度使用；這些是設計所需。
- `Diver_Mask` 原點距自身幾何中心較遠，是因裝備共用胸口座標系；珊瑚／海草與岩塊則保留根部／底部 pivot。
- 物件名稱、父子階層、共用 mesh、材質指派及非裝飾物件 transform 均與修正前一致；除沙地面繞序修復，幾何與 UV 未變。
- 主峰高 1.65 m、最高珊瑚約 1.394 m，保留約 0.256 m 高差。整體 X/Y 邊界及最高 Z 不變；根部淺埋使最低 Z 約降低 5.1 mm，在記錄的 1 cm 容差內。

根部檢查使用實際 mesh 的最低 2 mm 頂點帶向地形投射；表面相交另以 BVH 檢查。這些量測搭配多視角審視，不宣稱能證明場景中不存在任何自相交。與岩石的根部淺埋及角色裝備接合是刻意的幾何接合。

## 重建與證據

```bash
blender --background --factory-startup --threads 2 --python-exit-code 1 --python blender/scripts/02_detail.py
blender --background --factory-startup --threads 2 --python-exit-code 1 --python blender/scripts/03_inspect.py
```

模型：`blender/scenes/02_detail.blend`。渲染為 Eevee、1024×768、64 samples、AgX Medium High Contrast；完整建構與九張渲染約 5.5 秒（本機最後一次 log）。

- [technical_checks.json](technical_checks.json)：根部、管口、相交、法線、transform、origin、unused data。
- [metrics.json](metrics.json)：獨立 Blender Agent Studio inspector，hard gate 通過、issues 為空。
- [scene_comparison.json](scene_comparison.json)：基準與最終模型的不變條件及數值差異。
- [iteration_review.json](iteration_review.json)：修正前後判定與 `retain_repair` 決策。
- [render_manifest.json](render_manifest.json)：來源、模型與九張影像的 SHA-256 及渲染設定。
- `blender/revisions/detail_before_step05/`：修正前的來源、模型、色票、報告與影像。

可選的 Rust quality_report / compare_scenes runtime 尚未建置；已用 Blender 原生檢查及獨立 inspector 完成本階段驗證。
`preview_metrics.json` 是 Step 04 第一版的歷史資料，最終以 `metrics.json` 為準。

## 完成條件

- [x] 六張指定角度渲染與三張潛水員近照已輸出。
- [x] 視覺 checklist 已審視並通過。
- [x] 技術檢查無未處理錯誤。
- [x] 修正已回寫來源，乾淨程序重建成功。

下一步為 Step 06：正式匯出 GLB、重新匯入並驗證階層、材質與檔案大小。
