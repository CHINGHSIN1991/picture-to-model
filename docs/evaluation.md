# 評估紀錄(Evaluation)

> 對應 [ROADMAP.md](../ROADMAP.md) 各階段的評估與決策紀錄。
> Phase 0 的正式選型評估未逐項執行(直接以 Tripo 進入 PoC 驗證,運作良好);
> 2026-09-03 依 dev-log 實測回填評估表首版,並新增授權與商務條件表(D-3)。

---

## 評估表(首版,2026-09-03;數據來源 dev-log 實測)

> 「單家深測 + 本地對照」的結果整理。Meshy / Rodin 橫向待補;主觀分數(輪廓 / 背面 / topology)待人工評分後填入。
> 同一張輸入:`test-assets/hard-surface/vintage-radio/front.png`(655px)。

| 服務 | 物件 | 生成時間 | 面數(原始) | GLB | 材質類型 | 水密 | 輪廓還原 | 背面合理性 | Topology | 單次成本 |
|---|---|---|---|---|---|---|---|---|---|---|
| Tripo(API,PBR) | vintage-radio | 112.1s | 501,102 tris | 15.1 MB | **PBR**(basecolor + ORM + normal,2048²) | ✅ | | | | API 額度(待填) |
| Tripo | coral-mound | 107.5s | 502,558 tris | 16.2 MB | PBR | ✅ | | | | |
| Tripo | fishbowl | 104.9s | ~501K tris | — | PBR(玻璃烘成不透明,見附錄 A) | ✅ | | | | |
| TRELLIS.2(本地 trellis-mac,M4 24GB,無 Metal 加速) | vintage-radio | ≈10.3 分(451.7s + 貼圖 167s) | 1,824,936 → ~200K tris | 8.85 MB | 僅 basecolor(1024²) | ❌(觸發 cleanup 非水密防護) | | | | 0(本機電費) |
| Meshy | — | | | | | | | | | 待測 |
| Rodin | — | | | | | | | | | 待測 |

**現況結論**:Tripo 主方案(速度 5.5×、PBR 完整、水密);TRELLIS.2 為自架備援候補,觸發條件「月 API 費 > GPU 租金 + 維運」。

## 授權與商務條件(D-3,P0)

> 做 embed 產品 = 使用者把生成模型放上**他們的**商業網站。以下欄位是首個對外 Embed 案例的硬前置,未確認前不得對外交付。
> 填寫依據請以官方條款當日版本為準並**附上網址與查閱日期**;本表不憑記憶填寫。

| 服務 / 元件 | 生成資產商用權利(允許 / 限制 / 需授權) | 是否需標註來源 | 使用者轉授權(嵌入其商業網站) | 模型 license(開源限填) | API 價格 | Rate limit | SLA | 查閱來源 / 日期 |
|---|---|---|---|---|---|---|---|---|
| **Tripo(VAST)API** | 🔄 **官方 ToS 原文未取得**:`tripo3d.ai/terms` 與官方 blog 對自動抓取回 403,需人工開瀏覽器查閱。二手來源(搜尋摘要,**未核實**)稱:API 產出含商用權;免費方案產出公開於 gallery 並採 CC BY 4.0 非商用 | ⬜ 待查(二手來源稱付費 / API 不需標註,免費方案 CC BY) | ⬜ 待查(能否讓終端使用者把產出放上其商業網站 —— 本產品成立的關鍵條款) | — | ✅ 1 credit = $0.01;image-to-3D **20 credits(無貼圖)/ 30 credits(標準貼圖)**(developers.tripo3d.ai/en/pricing) | ⬜ 待查 | ⬜ 待查 | developers.tripo3d.ai/en/pricing,2026-09-04;ToS:tripo3d.ai/terms(待人工) |
| **TRELLIS.2(Microsoft)權重** | ✅ 允許(MIT) | 否(保留 license 聲明即可) | 允許 | ✅ **MIT** —— model card:「This model is released under the MIT License.」 | — | — | — | huggingface.co/microsoft/TRELLIS.2-4B,2026-09-04 |
| trellis-mac 相依:`briaai/RMBG-2.0`(去背) | ❌ **非商用**:「released under a CC BY-NC 4.0 license for non-commercial use. Commercial use is subject to a commercial agreement with BRIA.」 | 是(CC BY-NC) | ❌ | CC BY-NC 4.0 / BRIA 商業協議 | — | — | — | huggingface.co/briaai/RMBG-2.0,2026-09-04 |
| trellis-mac 相依:`facebook/dinov3-vitl16` | ✅ 允許(DINOv3 License 授予非專屬、全球、免權利金的使用 / 衍生 / 散布權;未禁止商用) | 研究發表需致謝;散布權重須附 License 全文 | 允許(散布須附 License) | **DINOv3 License**(自訂,2025-08-19;禁止逆向工程、禁止軍事 / 出口管制用途)—— 自訂授權建議法務過目 | — | — | — | github.com/facebookresearch/dinov3/blob/main/LICENSE.md,2026-09-04 |
| pipeline 相依:rembg(preprocess stage 去背) | ✅ 工具 MIT;**⚠️ rembg 預設模型是 `bria-rmbg`(= RMBG-2.0,BRIA 非商用)**。本專案已改為明確指定 **u2net(MIT via rembg)**,`preprocess_image.py` 對 bria-rmbg 直接拒絕 | 否 | 允許 | u2net / isnet-general-use / birefnet-general 皆「MIT (via rembg)」;bria-rmbg 為 BRIA License | — | — | — | github.com/danielgatis/rembg README,2026-09-04 |
| HDRI `studio_small_08`(Poly Haven) | CC0,可商用、可嵌入 | 否 | 允許 | CC0 | — | — | — | polyhaven.com(license 頁) |

**驗收(D-3)**:`[x]` TRELLIS.2 完成(MIT)。`[ ]` **Tripo 待人工查 ToS**(自動抓取被擋),重點三條:API 產出商用權、是否需標註、終端使用者轉授權。任一列為「限制 / 需授權」時,對外 Embed 前要先取得授權或改方案。

**已據此調整的實作**:自架路線(trellis-mac)若走商用,RMBG-2.0 去背必須換成 MIT 模型或取得 BRIA 協議;pipeline 的 preprocess 去背已強制 u2net。

---

## 附錄 A:AI 貼圖 PBR 品質評估(Phase 3 Step 3-2,2026-08-26)

### 方法

固定相機、整組光源(三點打光 + HDRI)繞 Z 軸旋轉 0° / 120° / 240° 各渲一張
(`uv run scripts/eval_textures.py output/<job_id>`,Cycles 64 samples / 800px):

- 高光與陰影**跟著光走** → 貼圖是乾淨的 PBR
- 亮部**黏在表面不動** → basecolor 烤死了光影(baked 殘留)

評估對象:Tripo API 內建 PBR 輸出(basecolor + ORM + normal,2048px)。
渲染圖存於 `output/<job_id>/eval/light_<deg>.webp`。

### 觀察

| 項目 | vintage-radio(hard-surface) | fishbowl(reflective) |
|---|---|---|
| 陰影方向 | ✅ 正確隨光旋轉 | ✅ 正確隨光旋轉 |
| 表面高光 | ✅ 機身光澤、金屬旋鈕與喇叭網的高光跟著光走,roughness 分布合理 | ✅ 球面頂部與邊緣的即時鏡面反射隨光移動,表面光澤感正確 |
| 金屬感 | ✅ 旋鈕/金屬件在不同角度呈現正確反射 | -(無金屬件) |
| baked 殘留 | ⚠️ 輕微:basecolor 有少量斑駁明暗(接近做舊質感,可接受) | ❌ 明顯:玻璃「窗」上的白色反光條紋與內容物亮部烤死在 basecolor,三個光照角度完全不動 |
| 其他 | - | ❌ 無透明:GLB 無 `alphaMode` / `KHR_materials_transmission`,玻璃是不透明表面(Phase 2 已記錄) |

### 結論

1. **第一版貼圖來源採用 Tripo API 內建 PBR 輸出**:
   hard-surface 與 organic 類的 roughness / metallic / normal 真實響應光照,達商品展示水準。
2. **品質不足時的 fallback**(依序):
   - 反光 / 透明類商品的 baked 反光:於 Phase 3 後續評估 **delighting(去光影)** 或 **Blender bake(Step 3-4)重出 basecolor**;
   - 玻璃透明感:需後製 **transmission 材質**(偵測玻璃區域、替換 shader),或在產品層面接受「烤圖玻璃」的呈現。
3. 反光類輸入照片建議在拍攝端減少環境反射(柔光箱、偏光鏡),從源頭降低 baked 殘留。
