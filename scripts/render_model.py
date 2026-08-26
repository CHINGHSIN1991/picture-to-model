"""Phase 2 Step 2-5: 渲染商品圖(跑在 uv venv)。

呼叫 Blender 的 render.py 產出帶 alpha 的 PNG,再以 Pillow 合成白底並轉出:
    preview.webp   1600px 商品主圖
    thumbnail.webp 400px 縮圖

用法:
    uv run scripts/render_model.py output/<job_id>
    uv run scripts/render_model.py output/<job_id> --samples 64 --resolution 1200
"""

import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image

from run_blender import run

THUMBNAIL_SIZE = 400
WEBP_QUALITY = 90


def png_to_webp(
    png_path: Path,
    job_dir: Path,
    background: str = "#FFFFFF",
    name: str = "preview",
    with_thumbnail: bool = True,
) -> dict:
    """透明 PNG → 合成背景色的 <name>.webp(可選 thumbnail.webp),回傳統計。"""
    img = Image.open(png_path).convert("RGBA")
    v = background.lstrip("#")
    bg_rgb = tuple(int(v[i : i + 2], 16) for i in (0, 2, 4))
    composed = Image.new("RGB", img.size, bg_rgb)
    composed.paste(img, mask=img.getchannel("A"))

    webp = job_dir / f"{name}.webp"
    composed.save(webp, quality=WEBP_QUALITY)
    stats = {f"{name}_webp_bytes": webp.stat().st_size}

    if with_thumbnail:
        thumb = composed.copy()
        thumb.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE), Image.LANCZOS)
        thumbnail = job_dir / "thumbnail.webp"
        thumb.save(thumbnail, quality=WEBP_QUALITY - 5)
        stats["thumbnail_webp_bytes"] = thumbnail.stat().st_size
        stats["thumbnail_px"] = THUMBNAIL_SIZE

    png_path.unlink()  # 中間檔,轉完即刪
    return stats


def render_job(
    job_dir: Path,
    samples: int = 128,
    resolution: int = 1600,
    azimuth: float = 30.0,
    elevation: float = 18.0,
    scene_json: Path | None = None,
) -> dict:
    """渲染一個 job 並轉 WebP,回傳統計。Blender 失敗時 raise RuntimeError。

    scene_json:編輯器輸出的 scene.json——camera / lights / render /
    materials_override 交給 render.py 套用,背景色在本層合成。
    """
    t0 = time.time()
    blender_args = [
        "--job-dir", str(job_dir),
        "--samples", str(samples),
        "--resolution", str(resolution),
        "--azimuth", str(azimuth),
        "--elevation", str(elevation),
    ]
    background = "#FFFFFF"
    if scene_json:
        blender_args += ["--scene-json", str(scene_json)]
        bg = json.loads(Path(scene_json).read_text()).get("environment", {}).get("background", {})
        if bg.get("type") == "color" and bg.get("value"):
            background = bg["value"]
    rc = run("render", blender_args)
    if rc != 0:
        raise RuntimeError(f"Blender render 失敗 (exit code {rc})")

    # scene.json 渲染是 poster(Embed 載入佔位 / og:image),與官方 preview 分開、不出縮圖
    name = "poster" if scene_json else "preview"
    meta_key = "poster_render" if scene_json else "render"
    png = job_dir / f"{name}.png"
    if not png.exists():
        raise RuntimeError(f"render.py 沒有產出 {png}")
    stats = png_to_webp(png, job_dir, background, name=name, with_thumbnail=not scene_json)

    meta_path = job_dir / "metadata.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta.setdefault(meta_key, {}).update(stats)
    meta[meta_key]["total_elapsed_sec"] = round(time.time() - t0, 1)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"[render_model] 完成 ({meta[meta_key]['total_elapsed_sec']}s) → {job_dir / f'{name}.webp'}")
    return meta[meta_key]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("job_dir", type=Path, help="output/<job_id>")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--resolution", type=int, default=1600)
    ap.add_argument("--azimuth", type=float, default=30.0)
    ap.add_argument("--elevation", type=float, default=18.0)
    ap.add_argument("--scene-json", type=Path,
                    help="編輯器輸出的 scene.json(camera/lights/render/materials_override 優先)")
    args = ap.parse_args()

    try:
        render_job(args.job_dir, args.samples, args.resolution, args.azimuth, args.elevation,
                   scene_json=args.scene_json)
    except RuntimeError as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
