# Sections — 選定 mockup 的逐段 3D 狀態

對應 [roadmap/09](../roadmap/09-website-mockup.md);選定 [final-homepage.png](final-homepage.png)(= `homepage-01.png`,編輯排版),
手機直式見 [final-homepage-mobile.png](final-homepage-mobile.png)。
Step 10 的元件數、Step 12 的 `config/sections.ts`、Step 13 的 `parts` 都從這份表來。
group 名稱與 [PROJECT_SPEC](../PROJECT_SPEC.md) 一致:`rocks`、`boulders`、`corals`、`kelp`、`diver`、`fish`。

## 這是什麼網站

**圖轉 3D 平台(Picture to Model)的產品頁**,不是珊瑚礁模型的介紹頁。
珊瑚礁是示範 asset:它從一張概念圖開始,所以用它來演示平台的四個階段。
每一段的 3D 零件動畫對應平台流程的一個階段:

| 平台階段 | 用示範 asset 演示的方式 | 零件 mode |
|---|---|---|
| 上傳一張圖 → graybox | 只剩岩層,由下往上堆起 | `rocks: stack` |
| 可重現的建模(零件都是程式碼) | 珊瑚與海草依序長出 | `corals + kelp: grow` |
| 瀏覽器裡調光(材質 / 光線 / 相機是設定檔) | 潛水員沿曲線下潛 | `diver: path` |
| 放進網站就會動(scroll / 游標 / 逐件動畫) | 魚群環繞進場 | `fish: orbit` |

Hero 先看到完整的礁;往下捲動時整座礁「倒帶」成空的岩層,接著依上表一段一段長回來。
模型同時繞行一整圈(旋轉 Y 累計 −360°),CTA 回到與 Hero 相同的角度。

## 表

「模型位置」是相對 Hero 取景的畫面位置;括號內是場景單位 x / y 偏移(礁石底部中心為 0,0),Step 10 已依截圖校正並寫入 `web/src/three/config/sections.ts`。
「旋轉」是模型繞 Y 軸的**累計**角度,一律負向遞減,CTA 寫 −360° 而不是 0°,避免 GSAP 走最長路徑。
「相機仰角」是 mockup render 的角度,給 Step 12 的 camera tween 參考。
「零件狀態」:`0` = rest,`1` = 該 group 在 spec 指定 mode 下的離開狀態;`1→0` 表示在這段內從離開狀態回到原位。
「UI 道具」是該段除了文案以外的 2D 元素(Vue 元件內的靜態 UI,不是 3D)。

| # | Section | Vue 元件 | 模型位置 | 旋轉 Y | 縮放 | 相機仰角 | 零件狀態(group: t) | 文案 | UI 道具 |
|---|---------|----------|----------|--------|------|----------|----------------------|------|---------|
| 1 | Hero「一張圖,變成會動的 3D 網站」 | `HeroSection` | 置中偏右(x +1.2, y 0) | 0° | 0.92 | 17° | 全部 0 | 左欄,標題 + 「上傳第一張圖」「看示範」 | nav、scroll hint |
| 2 | 上傳「從一張圖開始」 | `UploadSection` | 左側偏下(x −1.1, y −0.2) | −35° | 0.9 | 21° | rocks 1→0(`stack`);boulders 0;corals 1、kelp 1、diver 1、fish 1 | 右欄,三個數字(1 張圖 / 7,786 tri / 6 視角) | 左上「輸入 · 概念圖」卡片(`references/final-concept.png`)+ 箭頭指向模型 |
| 3 | 建模「每個零件都是程式碼」 | `ModelSection` | 右側(x +1.0, y −0.1) | −100° | 1.2 | 13° | corals 1→0、kelp 1→0(`grow`);rocks 0、boulders 0;diver 1、fish 1 | 左欄,三個數字(91 零件 / 1 材質 / 0.6 MB) | 左下 `model.spec.json` 程式碼卡片 |
| 4 | 調光「材質、光線、相機,全是設定檔」 | `ControlsSection` | 左側(x −1.5, y +0.1) | −160° | 1.0 | 9° | diver 1→0(`path`);rocks、boulders、corals、kelp 0;fish 1 | 右欄 | 右下 `lighting.json` 滑桿面板(曝光 / 主光 / 霧氣 / 水色);Step 10 可直接接 Step 08 的 lightingConfig |
| 5 | 互動「放進網站,就會動」 | `InteractionSection` | 置中偏右(x +0.9, y 0) | −230° | 0.9 | 26° | fish 1→0(`orbit`);其餘 0 | 左欄 | 左下功能 chips(scroll 敘事 / 游標跟隨 / 逐件動畫 / 手機 fallback / 離開畫面暫停 / DPR 上限) |
| 6 | CTA「用你的下一張圖試試看」 | `CtaSection` | 置中偏下(x 0, y −0.7),上緣被文字區壓住 | −360° | 0.85 | 30° | 全部 0 | 置中,「上傳一張圖」「看完整流程」 | footer |

## 段落之間的過渡

| 過渡 | 零件 | 說明 |
|---|---|---|
| 1 → 2 | rocks、corals、kelp、diver、fish:0→1;boulders 維持 0 | 「倒帶」回到只有輸入圖的狀態:岩塊沉下、珊瑚海草縮回、潛水員回到畫面頂、魚群環繞退場;沙地與小石塊留在原地當錨 |
| 2 → 3、3 → 4、4 → 5 | 無 | 只有位置 / 旋轉 / 縮放 / 相機在動;零件動畫都在各段停留時發生 |
| 5 → 6 | 無 | 模型沉到畫面下方並縮小,旋轉收尾到 −360° |

上表每段的「零件狀態」是該段 pin 住時從頭到尾的變化;段與段之間沒寫的 group 維持前一段結束時的值。
`explode` mode 沒有任何 section 用到,PROJECT_SPEC 已依規則刪除該列。

Step 12 的實際停留方式：每個 section 外層增加 `.story-step`，四個流程段的外層高度為內容高度 + 一個 viewport。
內容以 CSS sticky 停在畫面上，GSAP 每段一個 ScrollTrigger，先插值到進場狀態，再於額外距離內播放零件。
內容高於視窗時使用負的 sticky top，先讓使用者讀完內容再停留。減少動態效果時沒有額外停留，直接切換段落完成狀態。

## 每段的版面

- 桌機 1440×900,每段一個 viewport 高;模型永遠在固定的 Three.js canvas 上,文字與 UI 道具捲過它。
- 文字區固定 520 px 寬,標題用襯線體(Baskerville / Songti TC),內文與 eyebrow 用無襯線(Avenir Next / PingFang TC)。
- 段落編號 01–04 是 300 px 的低不透明度襯線數字,放在與模型相對的一角。
- UI 道具是半透明深藍玻璃卡片(`mockups/src/base.css` 的 `.prop`),放在文案同側的下方或模型旁,不壓到模型。
- 背景是單一深藍漸層(#1d6fc4 → #072a66),對應 Step 08 的水色;上方有淡光束,CTA 再加深一階。
- 手機(390 寬):文字 → UI 道具 → 模型,模型寬 112% 置中;Step 14 以這個順序放靜態圖 fallback。

## 來源與重現

mockup 不是影像生成,而是 Blender 透明背景 render + HTML 排版:

```bash
blender --background --factory-startup --threads 2 --python-exit-code 1 --python blender/scripts/04_mockup_renders.py
cd web && bun run mockups
```

前者讀 `02_detail.blend`,依本表的旋轉、仰角與零件可見性輸出 `blender/renders/mockup/s1–s6.png` 與 `manifest.json`;
後者用 Chrome 把 `mockups/src/homepage-0N.html` 截成桌機與手機整頁 PNG。
