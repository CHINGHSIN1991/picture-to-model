# Picture to Model

將圖片轉成可調整、匯出與嵌入網站的 3D 模型。目前實作 **Phase 1：本機專案骨架與無付費流程**。

目前可建立專案、上傳圖片、追蹤背景任務、旋轉／縮放預覽模型，重新整理或重啟服務後繼續操作。**所有生成皆使用 fake provider，回傳固定示範 GLB，不會根據圖片重建、不呼叫 AI，也不產生費用。** 真實供應商、模型編輯與三種網站整合選項留在後續階段。

## 開始使用

需要 Python 3.12 以上、[uv](https://docs.astral.sh/uv/)、Node.js 22.12 以上與 npm。使用專案內的 `uv.lock` 與 `web/package-lock.json` 安裝固定版本：

```sh
uv sync --locked
npm ci --prefix web
uv run python scripts/dev.py
```

開啟 <http://127.0.0.1:5173>。啟動器會一起執行 API、worker 與前端，按 Ctrl+C 停止所有程序。啟動失敗時會停止其餘程序並顯示錯誤；請先確認 8000 與 5173 連接埠未被佔用。此啟動器適用 macOS／Linux。

不需要複製 `.env.example` 或填寫金鑰；第一階段不載入 `.env`，也不需要 Blender 或 GPU。

## 操作流程

1. 建立並命名專案。
2. 上傳 PNG／JPEG：最大 10 MB、最長邊 4096 px、總像素 16 MP。後端實際解碼驗證並清除圖片 metadata。
3. 啟動示範生成，畫面會輪詢排隊、生成、下載、驗證與完成狀態。
4. 完成後以滑鼠拖曳及滾輪操作 3D 預覽。各張圖片目前都會取得相同示範模型。
5. 重新整理或回到專案列表，再次開啟已儲存的模型。

若任務停在排隊，確認 worker 已啟動；API 不會在 HTTP 請求內執行生成工作。

## 分別啟動服務

在專案根目錄的三個終端執行：

```sh
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```sh
uv run python -m backend.app.worker
```

```sh
npm run dev --prefix web
```

API 文件：<http://127.0.0.1:8000/docs>。前端透過 Vite 將 `/api` 代理到本機 API。開發服務只綁定 loopback；目前沒有登入機制，不適合公開部署。

## 資料與設定

| 設定 | 預設 | 用途 |
| --- | --- | --- |
| `PTM_DATA_DIR` | `output/data` | SQLite 與私有圖片／模型資產；相對路徑以專案根目錄解析 |
| `PTM_LOCAL_OWNER` | `local-owner` | 本機擁有者；由伺服器指定，不接受用戶端身分冒用 |
| `PTM_WEB_ORIGIN` | `http://127.0.0.1:5173` | API 接受的開發介面來源；啟動器會依前端連接埠設定 |

需要自訂時，在啟動前設定環境變數，例如：

```sh
export PTM_DATA_DIR=output/my-workspace
uv run python scripts/dev.py
```

API 與 worker 必須使用相同設定。資料不放在 `web/public`；下載會經由 API 檢查所屬專案。`output/` 已被 Git 忽略。SQLite migration 在啟動時套用，已建立的資料不會因重新啟動被清除。

任務進度與 provider task ID 都寫入 SQLite。worker 以 lease 領取工作，意外停止後可在 lease 到期時恢復；示範供應商採可重現 ID，不需要外部網路。這只驗證本機恢復機制，不代表已處理真實第三方供應商的付費提交語義。

## 檢查

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
npm run lint --prefix web
npm run format:check --prefix web
npm run build --prefix web
```

瀏覽器端到端測試使用獨立測試資料與連接埠，驗證上傳、任務完成、GLB 預覽與重新整理：

```sh
cd web
npx playwright install chromium
npm run test:e2e
```

測試不需要任何 AI 金鑰。Chromium 首次安裝需要網路；日常測試資料放在被忽略的 `output/` 下。

## 結構與下一階段

- `backend/`：FastAPI、SQLite、私有儲存、供應商介面、worker 與測試。
- `web/`：React／TypeScript／Vite 工作台及 Three.js 預覽。
- `fixtures/`：本專案自行製作的固定測試模型。
- `scripts/dev.py`：本機服務啟動器。
- [產品規格](docs/SPEC.md)、[技術架構](docs/ARCHITECTURE.md)、[實作步驟](ROADMAP.md)。

Phase 0 的真實生成品質、價格與供應商比較尚未執行。下一階段應先完成該選型，再接入一個真實 provider；目前的固定模型不能作為生成品質證據。
