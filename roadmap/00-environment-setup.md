# Step 00 — 環境準備

## 目標

把整條 pipeline 需要的工具裝好,並確認 Codex 能透過 Blender Agent Studio 控制 Blender。

## 為什麼

Blender Agent Studio 的作用是讓 Codex 不只是「產生 Blender Python」,
而是可以**建模、render、從不同角度檢查、驗證 export**。
沒有它,後面每一步的「render 檢查」與「GLB 驗證」都要手動做。

## 需要安裝的東西

| # | 工具 | 用途 | 版本要求 |
|---|------|------|----------|
| 1 | Blender | 3D 建模 / render / export | 建議 **5.2 LTS**(Blender Agent Studio 文件建議) |
| 2 | Codex | AI agent,驅動整個流程 | 最新版 |
| 3 | Bun | Blender Agent Studio 完整 plugin 模式需要 | **1.3.5+** |
| 4 | Blender Agent Studio | Codex plugin:建模 / render / 驗證 skills | 最新 |
| 5 | Blender to Web | 影片作者整理的工作流程 repo | clone 即可 |

## 操作步驟

### 1. 安裝 Blender

- 從 https://www.blender.org/download/ 安裝 5.2 LTS。
- macOS 預設路徑:`/Applications/Blender.app/Contents/MacOS/Blender`

### 2. 安裝 Codex

依官方指示安裝 Codex CLI,確認 `codex --version` 可執行。

### 3. 安裝 Bun

```bash
curl -fsSL https://bun.sh/install | bash
bun --version   # 需要 >= 1.3.5
```

### 4. 安裝 Blender Agent Studio plugin

```bash
codex plugin marketplace add ifBars/blender-agent-studio
codex plugin add blender-agent-studio@blender-agent-studio
```

### 5. 確認 Blender CLI 找得到

```bash
blender --version
```

找不到的話,設定 `BLENDER_EXECUTABLE`:

macOS (zsh):
```bash
export BLENDER_EXECUTABLE="/Applications/Blender.app/Contents/MacOS/Blender"
# 建議寫進 ~/.zshrc
echo 'export BLENDER_EXECUTABLE="/Applications/Blender.app/Contents/MacOS/Blender"' >> ~/.zshrc
```

Windows (PowerShell):
```powershell
$env:BLENDER_EXECUTABLE = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
```

### 6. Clone Blender-to-Web repo

```bash
git clone https://github.com/cth9191/blender-to-web.git
cd blender-to-web
```

這個 repo 是影片裡 APERTURE 實驗整理出來的工作流程,包含:
- prompt library
- Blender source
- Three.js 範例
- mobile fallback 實作

**用途:當參考,不是照抄。** 本專案後面會改用 Vue 3 + Vite 的結構(見 Step 10)。

### 7. 建立本專案目錄骨架

```bash
cd /Users/chinghsinc/Develop/blender-to-model
mkdir -p references blender/scripts blender/scenes blender/renders/graybox blender/renders/final export mockups web
```

## 驗證環境是否 OK

請 Codex 執行一次 smoke test:

```
Use the Blender Agent Studio skills to:
1. open a new empty Blender scene
2. add a cube
3. render a single frame at 512x512
4. save the .blend to blender/scenes/smoke-test.blend
5. save the Python script used to blender/scripts/smoke-test.py

Report the Blender version detected and whether rendering succeeded.
```

## 完成條件 (Definition of Done)

- [ ] `blender --version` 顯示 5.2.x
- [ ] `bun --version` ≥ 1.3.5
- [ ] `codex plugin list` 看得到 blender-agent-studio
- [ ] smoke test 有產生 render 圖、`.blend` 與 `.py`
- [ ] 專案目錄骨架已建立

## 常見問題

- **Codex 說找不到 Blender** → 確認 `BLENDER_EXECUTABLE` 在 Codex 啟動的 shell 中有生效(重開終端)。
- **plugin 功能不完整** → 檢查 Bun 版本,完整 plugin 模式需要 1.3.5+。
- **render 很慢** → smoke test 階段用 Eevee 與低解析度即可,不要用 Cycles。

## 參考

- Blender Agent Studio: https://github.com/ifBars/blender-agent-studio
- Blender to Web: https://github.com/cth9191/blender-to-web
