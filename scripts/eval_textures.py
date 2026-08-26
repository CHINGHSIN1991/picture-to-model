"""Phase 3 Step 3-2: PBR 貼圖品質評估 — 固定相機、旋轉打光(跑在 uv venv)。

同一模型、同一相機,把整組光源(含 HDRI)轉不同角度各渲一張:
- 高光「跟著光走」→ 貼圖是乾淨的 PBR
- 高光「黏在表面」→ basecolor 烤死了光影(baked 殘留)

用法:
    uv run scripts/eval_textures.py output/<job_id>
    uv run scripts/eval_textures.py output/<job_id> --rotations 0 90 180 270

輸出 output/<job_id>/eval/light_<deg>.webp(預設 0/120/240 三張)。
"""

import argparse
import sys
import time
from pathlib import Path

from PIL import Image

from run_blender import run

DEFAULT_ROTATIONS = [0, 120, 240]


def render_rotation(job_dir: Path, degrees: float, samples: int, resolution: int) -> Path:
    eval_dir = job_dir / "eval"
    eval_dir.mkdir(exist_ok=True)
    png = eval_dir / f"light_{int(degrees):03d}.png"
    rc = run(
        "render",
        [
            "--input", str(job_dir / "model_high.glb"),
            "--output", str(png),
            "--samples", str(samples),
            "--resolution", str(resolution),
            "--light-rotation", str(degrees),
        ],
    )
    if rc != 0:
        raise RuntimeError(f"render 失敗 (光照 {degrees}°, exit code {rc})")

    img = Image.open(png).convert("RGBA")
    white = Image.new("RGB", img.size, (255, 255, 255))
    white.paste(img, mask=img.getchannel("A"))
    webp = png.with_suffix(".webp")
    white.save(webp, quality=85)
    png.unlink()
    return webp


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("job_dir", type=Path, help="output/<job_id>")
    ap.add_argument("--rotations", type=float, nargs="+", default=DEFAULT_ROTATIONS)
    ap.add_argument("--samples", type=int, default=64, help="評估用,低於正式渲染即可")
    ap.add_argument("--resolution", type=int, default=800)
    args = ap.parse_args()

    if not (args.job_dir / "model_high.glb").exists():
        sys.exit(f"找不到 {args.job_dir}/model_high.glb")

    t0 = time.time()
    for deg in args.rotations:
        out = render_rotation(args.job_dir, deg, args.samples, args.resolution)
        print(f"[eval] 光照 {deg:g}° → {out}")
    print(f"[eval] 完成 ({time.time() - t0:.1f}s),共 {len(args.rotations)} 張")


if __name__ == "__main__":
    main()
