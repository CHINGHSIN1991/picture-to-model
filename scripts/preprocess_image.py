"""Stage preprocess(D-2):圖片品質前處理(跑在 uv venv)。

pipeline 第 1 站,在 generate 之前。輸入品質是生成品質的第一槓桿——
在花掉 API 額度之前先把圖修好或擋下:

1. 解析度下限檢查(fail fast,預設 1024px)
2. 去背(rembg;venv 缺 onnxruntime 時退到 `uvx --python 3.12 rembg`;都不行則記警告續跑)
3. 主體佔比檢查與置中重取景(alpha bounding box,目標佔比 0.75,允許 0.70~0.80)
4. 輸出正規化:方形 1024² RGBA PNG → <job>/input/front_preprocessed.png;原圖另存 input/front.<ext> 不覆蓋

用法:
    uv run scripts/preprocess_image.py test-assets/hard-surface/vintage-radio/front.png --out-dir output/<job_id>
    uv run scripts/preprocess_image.py <image> --out-dir <dir> --no-remove-bg      # 只做取景與正規化
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

MIN_RESOLUTION = 1024
OUTPUT_SIZE = 1024
TARGET_RATIO = 0.75
RATIO_RANGE = (0.70, 0.80)
ALPHA_THRESHOLD = 16          # alpha 大於此值視為主體
COLOR_DIFF_THRESHOLD = 24     # 無 alpha 時,與角落背景色差大於此值視為主體
UPSCALE_WARN = 1.5            # 放大倍率超過此值記警告(細節不足)
REMBG_PYTHON = "3.12"         # onnxruntime 尚無 3.14 wheel;uvx 另開環境跑 rembg
REMBG_TIMEOUT = 900           # 首次執行會下載 u2net 權重(~170MB)


# ---------------------------------------------------------------- 去背
def _rembg_inprocess(img: Image.Image) -> Image.Image | None:
    try:
        from rembg import remove  # type: ignore
    except ImportError:
        return None
    return remove(img).convert("RGBA")


def _rembg_uvx(src: Path, work_dir: Path) -> Image.Image | None:
    if not shutil.which("uvx"):
        return None
    out = work_dir / "_rembg.png"
    cmd = ["uvx", "--python", REMBG_PYTHON, "--from", "rembg[cpu,cli]", "rembg", "i", str(src), str(out)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=REMBG_TIMEOUT)
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"[preprocess] uvx rembg 失敗: {exc}")
        return None
    if proc.returncode != 0 or not out.exists():
        print(f"[preprocess] uvx rembg exit {proc.returncode}: {proc.stderr.strip()[-400:]}")
        return None
    img = Image.open(out).convert("RGBA")
    img.load()
    out.unlink()
    return img


def remove_background(img: Image.Image, src: Path, work_dir: Path) -> tuple[Image.Image | None, str]:
    """回傳 (RGBA 去背圖或 None, 方法名)。"""
    result = _rembg_inprocess(img)
    if result is not None:
        return result, "rembg"
    result = _rembg_uvx(src, work_dir)
    if result is not None:
        return result, f"rembg(uvx py{REMBG_PYTHON})"
    return None, "unavailable"


# ---------------------------------------------------------------- 主體 bbox
def _corner_color(img: Image.Image) -> tuple[int, int, int]:
    rgb = img.convert("RGB")
    w, h = rgb.size
    corners = [rgb.getpixel((0, 0)), rgb.getpixel((w - 1, 0)), rgb.getpixel((0, h - 1)), rgb.getpixel((w - 1, h - 1))]
    return tuple(sum(c[i] for c in corners) // 4 for i in range(3))  # type: ignore[return-value]


def subject_bbox(img: Image.Image, has_alpha: bool) -> tuple[int, int, int, int] | None:
    if has_alpha:
        mask = img.getchannel("A").point(lambda a: 255 if a > ALPHA_THRESHOLD else 0)
    else:
        bg = Image.new("RGB", img.size, _corner_color(img))
        mask = ImageChops.difference(img.convert("RGB"), bg).convert("L").point(
            lambda v: 255 if v > COLOR_DIFF_THRESHOLD else 0)
    return mask.getbbox()


def bbox_ratio(bbox: tuple[int, int, int, int] | None, size: tuple[int, int]) -> float | None:
    if not bbox:
        return None
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    return round(max(bw, bh) / max(size), 3)


# ---------------------------------------------------------------- 主流程
def preprocess(
    image: Path,
    out_dir: Path,
    min_resolution: int = MIN_RESOLUTION,
    output_size: int = OUTPUT_SIZE,
    target_ratio: float = TARGET_RATIO,
    remove_bg: bool = True,
) -> dict:
    """處理單張圖,寫入 out_dir/input/,合併統計到 out_dir/metadata.json 的 preprocess 欄位。

    解析度低於下限時 raise ValueError(fail fast,訊息可直接顯示給使用者)。
    回傳 dict 的 output 為相對 out_dir 的路徑。
    """
    t0 = time.time()
    warnings: list[str] = []
    input_dir = out_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    src = Image.open(image)
    src = ImageOps.exif_transpose(src) or src
    w, h = src.size
    if min(w, h) < min_resolution:
        raise ValueError(
            f"輸入圖片解析度 {w}×{h} 低於下限 {min_resolution}×{min_resolution},"
            f"細節不足以重建 3D 模型。請提供較大的圖片(建議 ≥ {min_resolution}px,主體清楚、背景乾淨)。")

    kept = input_dir / f"front{image.suffix.lower()}"
    if image.resolve() != kept.resolve():
        shutil.copy(image, kept)

    if src.mode == "P" or (src.mode == "RGBA" and src.getextrema()[3][0] < 255):  # 已有透明像素
        has_alpha = True
        img = src.convert("RGBA")
    else:
        has_alpha = False
        img = src.convert("RGBA")

    bg_method = "skipped"
    background_removed = False
    if remove_bg and not has_alpha:
        cut, bg_method = remove_background(src.convert("RGB"), kept, input_dir)
        if cut is not None:
            img, has_alpha, background_removed = cut, True, True
        else:
            warnings.append("background_removal_unavailable: rembg 不可用,保留原背景(背景雜訊會被 AI 當成幾何線索)")
    elif has_alpha:
        bg_method = "source_alpha"

    bbox = subject_bbox(img, has_alpha)
    if not bbox:
        warnings.append("subject_not_found: 找不到主體,跳過取景")
        bbox = (0, 0, w, h)
    if not has_alpha:
        warnings.append("bbox_heuristic: 無 alpha,主體範圍以角落背景色差估算")
    ratio_before = bbox_ratio(bbox, (w, h))

    # 置中重取景:以主體最長邊 / 目標佔比為方形邊長,超出邊界處補透明(或原背景色)
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    side = max(int(round(max(bw, bh) / target_ratio)), 8)
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    left, top = int(round(cx - side / 2)), int(round(cy - side / 2))
    crop_box = (left, top, left + side, top + side)
    fill = (0, 0, 0, 0) if has_alpha else (*_corner_color(img), 255)
    canvas = Image.new("RGBA", (side, side), fill)
    canvas.paste(img, (-left, -top))
    scale = output_size / side
    if scale > UPSCALE_WARN:
        warnings.append(f"upscaled_{scale:.2f}x: 主體原始像素偏少,放大 {scale:.2f} 倍")
    out_img = canvas.resize((output_size, output_size), Image.LANCZOS)

    ratio_after = bbox_ratio(subject_bbox(out_img, has_alpha), out_img.size)
    if ratio_after is not None and not (RATIO_RANGE[0] <= ratio_after <= RATIO_RANGE[1]):
        warnings.append(f"subject_ratio_out_of_range: {ratio_after} 不在 {RATIO_RANGE[0]}~{RATIO_RANGE[1]}")

    out_path = input_dir / "front_preprocessed.png"
    out_img.save(out_path, "PNG", optimize=True)

    meta = {
        "source": str(image),
        "kept_source": str(kept.relative_to(out_dir)),
        "output": str(out_path.relative_to(out_dir)),
        "original_size": [w, h],
        "output_size": [output_size, output_size],
        "subject_bbox": list(bbox),
        "subject_ratio_before": ratio_before,
        "subject_ratio_after": ratio_after,
        "target_ratio": target_ratio,
        "crop_box": list(crop_box),
        "scale": round(scale, 3),
        "background_removed": background_removed,
        "background_method": bg_method,
        "min_resolution": min_resolution,
        "warnings": warnings,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    meta_path = out_dir / "metadata.json"
    full = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    full["preprocess"] = meta
    meta_path.write_text(json.dumps(full, ensure_ascii=False, indent=2))

    print(f"[preprocess] {w}×{h} → {output_size}² · 主體佔比 {ratio_before} → {ratio_after}"
          f" · 去背 {bg_method} · {meta['elapsed_sec']}s → {out_path}")
    for msg in warnings:
        print(f"[preprocess] ⚠ {msg}")
    return meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", type=Path)
    ap.add_argument("--out-dir", type=Path, help="輸出目錄(預設 output/preprocess-<圖檔名>)")
    ap.add_argument("--min-resolution", type=int, default=MIN_RESOLUTION)
    ap.add_argument("--size", type=int, default=OUTPUT_SIZE, help="輸出邊長(px)")
    ap.add_argument("--target-ratio", type=float, default=TARGET_RATIO)
    ap.add_argument("--no-remove-bg", action="store_true", help="不去背,只做取景與正規化")
    args = ap.parse_args()
    if not args.image.exists():
        sys.exit(f"找不到圖片: {args.image}")
    out_dir = args.out_dir or Path("output") / f"preprocess-{args.image.stem}"
    try:
        preprocess(args.image, out_dir, min_resolution=args.min_resolution, output_size=args.size,
                   target_ratio=args.target_ratio, remove_bg=not args.no_remove_bg)
    except ValueError as exc:
        sys.exit(f"[preprocess] {exc}")


if __name__ == "__main__":
    main()
