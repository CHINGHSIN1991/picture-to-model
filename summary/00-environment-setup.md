# Step 00 總結 — 環境準備

對應 roadmap:[roadmap/00-environment-setup.md](../roadmap/00-environment-setup.md)
狀態:完成(2026-10-08 建立目錄骨架;smoke test 於 Step 03 前通過)

## 代表結果

![smoke test render](assets/00-smoke-test.png)

512×512 的 smoke test render:一顆 cube、一盞 sun、沒有 world,所以背景全黑。這張圖只證明一件事:headless Blender 能從空場景建物件並寫出 PNG。

代表程式碼:render engine fallback([smoke-test.py:49-54](../blender/scripts/smoke-test.py#L49-L54))

```python
for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
    try:
        scene.render.engine = engine
        break
    except TypeError:
        continue
```

執行成功時的終端輸出:

```
SMOKE_TEST_OK blender=5.2.0 LTS engine=BLENDER_EEVEE
  render: .../blender/renders/smoke-test.png
  blend:  .../blender/scenes/smoke-test.blend
```

## 這一步做了什麼

1. 安裝 pipeline 需要的工具:Blender 5.2 LTS、Codex CLI、Bun、Blender Agent Studio plugin,並 clone `blender-to-web` 作為參考(與本 repo 同層)。
2. 設定 `BLENDER_EXECUTABLE` 環境變數,讓 Codex / 終端都能找到 Blender。
3. 建立專案目錄骨架:`references/`、`blender/{scripts,scenes,renders/graybox,renders/final}`、`export/`、`mockups/`、`web/`。
4. 寫一個不經 Codex、直接 headless 跑的 smoke test:[blender/scripts/smoke-test.py](../blender/scripts/smoke-test.py)。

## 產出

| 檔案 | 內容 |
|---|---|
| `blender/scripts/smoke-test.py` | 空場景 → 加 cube → 512×512 render → 存 `.blend` |
| `blender/renders/smoke-test.png` | 灰色 cube、黑背景(沒有 world,屬預期) |
| `blender/scenes/smoke-test.blend` | smoke test 場景 |
| `README.md` 環境表 | 工具、版本、安裝指令 |

## 技術說明

- **從真正空的場景開始**:`bpy.ops.wm.read_factory_settings(use_empty=True)` 會移除預設 cube / camera / light。之後每一個建模腳本都沿用這個開頭,這是「可重現」的基礎。
- **render engine fallback**:腳本依序嘗試 `BLENDER_EEVEE_NEXT` → `BLENDER_EEVEE` → `BLENDER_WORKBENCH`,用 `try/except TypeError` 吃掉不存在的 engine id。Blender 4.x 與 5.x 的 Eevee enum 名稱不同,這個寫法讓同一支腳本跨版本可跑。
- **物件用 data API 建立,不用 ops**:camera 與 light 都是 `bpy.data.*.new()` 再 `scene.collection.objects.link()`,避免 `bpy.ops` 對 context / 選取狀態的依賴,在 `--background` 模式下更穩。
- **實際偵測到的版本**:後續 metrics 顯示 Blender 5.2.0 LTS(build hash `fbe6228777e7`),符合 roadmap 要求。

## Takeaway

- **先確認 headless 路徑能走通,再接 agent**。smoke test 不經 Codex,所以後面任何「render 失敗」都能先排除環境問題。
- **render engine 名稱要寫成 fallback 列表**,不要寫死一個 enum;這個模式在 Step 04 的 `02_detail.py` 又用了一次。
- **路徑一律相對 repo root 計算**(`ROOT = dirname(__file__)/../..`),腳本從任何 cwd 執行都正確。
- 本專案的 Blender 建模最後主要靠 `blender --background --python` 直接跑腳本;Blender Agent Studio 的角色是提供 asset inspector(產出 `metrics.json`)與 modeling 流程範本,而不是每一步都必須經過它。
