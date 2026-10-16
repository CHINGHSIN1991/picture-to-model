# 單峰灰模重建 — 2026-10-16

範圍：使用者要求清空舊 graybox，依參考圖重建為只有一個山峰的珊瑚礁。階段仍為 Step 03 無材質灰模。

## 結果

- 從空場景重建，舊的多座高岩柱配置已移除。
- Rock_Peak_001 改為連續、閉合、向上收窄的階梯山體；最高點只有一個，位於 (0.28, 0.25, 1.65) m。
- 主山體外框約 3.32 × 2.25 × 1.65 m；六塊山腳岩高度介於 0.25–0.55 m。
- 大型珊瑚改放兩側低坡，最高珊瑚約 1.16 m，低於主峰約 0.49 m；峰頂保留清楚留白。
- 沙地縮為 4.5 × 3.6 m；DIVER_LENGTH 現在控制潛水員長度，維持上方懸浮位置。
- 所有動態群組、潛水員子物件、共用 variant meshes 與 Scene_Root 階層保留。
- MODEL_PLAN.md 已同步單峰需求。

## 驗證

Blender 5.2.0 LTS（fbe6228777e7）從空場景執行成功，並在獨立程序重新開啟產物。
91 個 mesh objects，26 個 unique meshes；7,786 scene triangles，2,098 unique triangles。
主山體只有一個 connected component，沒有開放邊界、非流形邊、退化面或無效頂點。
全場景無無效頂點、退化面、零長度邊及 loose elements。全場景的 48 條開放邊是沙地平面外圈。
已開啟檢視最終 hero、六視角總覽與同相機前後對照；單峰、寬底、向上收束在前後側視角均可辨識。
無材質、無 UV、無動畫及無 GLB 是此灰模階段的預期設定；細節與 reference 的逐項精準對齊不在本次單峰調整範圍。

## 檔案

- Source：blender/scripts/01_graybox.py
- Scene：blender/scenes/01_graybox.blend
- 六視圖：blender/renders/graybox/{hero,front,left,right,back,top}.png
- 總覽：blender/renders/graybox/contact_sheet.png（上排 hero/front/left，下排 right/back/top）
- 同相機對照：blender/renders/graybox/before_after.png（左舊／右新）
- 資產量測：blender/renders/graybox/metrics.json
- 單峰檢查：blender/renders/graybox/single_peak_checks.json
- 迭代紀錄：blender/renders/graybox/iteration_review.json
- 舊版封存：blender/revisions/graybox_before_single_peak/（不載入目前場景）

重建指令：`blender --background --factory-startup --python-exit-code 1 --python blender/scripts/01_graybox.py`。
