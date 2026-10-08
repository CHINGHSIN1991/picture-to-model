# picture-to-model

從「概念圖」到「可互動的 Three.js 網站」的 Blender → Web 3D 工作流程。
完整步驟見 [roadmap/README.md](roadmap/README.md),一次做一步,達到每步的完成條件再往下。

## 目錄結構

```
roadmap/              步驟文件(00–17)與 pipeline 總覽
references/           概念圖、最終 reference(Step 01–02)
blender/
  scripts/            可從空場景重現的 Blender Python source(必存)
  scenes/             .blend 檔
  renders/graybox/    graybox 多角度 render(Step 03)
  renders/final/      完整模型 render(Step 05)
export/               驗證過的 .glb(Step 06)
mockups/              網站 mockup 圖(Step 09)
web/                  Vue 3 + Vite + Three.js 專案(Step 10)
```

## 環境(Step 00)

| 工具 | 需求 | 安裝方式 |
|---|---|---|
| Blender | 5.2 LTS | https://www.blender.org/download/ |
| Codex CLI | 最新 | `npm install -g @openai/codex` |
| Bun | ≥ 1.3.5 | `curl -fsSL https://bun.sh/install \| bash` |
| Blender Agent Studio | 最新 | `codex plugin marketplace add ifBars/blender-agent-studio` 然後 `codex plugin add blender-agent-studio@blender-agent-studio` |
| blender-to-web | 參考用 | clone 於 `../blender-to-web`(與本 repo 同層) |

`~/.zshrc` 需有:

```bash
export BLENDER_EXECUTABLE="/Applications/Blender.app/Contents/MacOS/Blender"
```

### Smoke test

不經 Codex、直接用 Blender headless 驗證環境:

```bash
blender --background --python blender/scripts/smoke-test.py
```

會產生 `blender/renders/smoke-test.png` 與 `blender/scenes/smoke-test.blend`。
經 Codex + Blender Agent Studio 的版本請用 [roadmap/00-environment-setup.md](roadmap/00-environment-setup.md) 內的 prompt。

## 原則

1. 先概念圖,再建模。
2. 先 graybox,再細節。
3. 每一步都 render 檢查。
4. 永遠保存 Blender Python source,讓模型可重現。
5. 網站先做 mockup。
6. Web 效能(mobile fallback、offscreen pause、DPR 限制)是設計的一部分。
