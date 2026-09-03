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
| **Tripo(VAST)API** | ⬜ 待查(Terms of Service:生成物歸屬、付費方案與免費方案差異) | ⬜ 待查 | ⬜ 待查(是否允許整合進自家產品再供第三方商用) | — | ⬜ 待查(每次 image_to_model 額度) | ⬜ 待查 | ⬜ 待查 | |
| **TRELLIS.2(Microsoft)權重** | ⬜ 待查 | ⬜ 待查 | ⬜ 待查 | ⬜ 待查(HuggingFace model card 的 license 欄;**Step 5-5 灰度切換的硬前置**) | — | — | — | |
| trellis-mac 相依:`briaai/RMBG-2.0`(去背) | ⬜ 待查 —— gated model,dev-log 記錄需同意條款才能下載;**疑為非商用授權,自架商用前必須確認** | ⬜ | ⬜ | ⬜ 待查 | — | — | — | |
| trellis-mac 相依:`facebook/dinov3-vitl16` | ⬜ 待查(Meta 表單審核制,授權條款待讀) | ⬜ | ⬜ | ⬜ 待查 | — | — | — | |
| pipeline 相依:rembg(preprocess stage 去背) | 工具本身 MIT;預設 u2net 權重 Apache-2.0 —— ⬜ 待覆核;若改用 BiRefNet / isnet 等其他權重需逐一查 | — | — | ⬜ | — | — | — | |
| HDRI `studio_small_08`(Poly Haven) | CC0,可商用、可嵌入 | 否 | 允許 | CC0 | — | — | — | polyhaven.com(license 頁) |

**驗收(D-3)**:`[ ]` Tripo 與 TRELLIS.2 兩列填完並附來源網址與日期。任一列為「限制 / 需授權」時,對外 Embed 前要先取得授權或改方案。

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
