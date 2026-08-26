"""Phase 3 Step 3-1: 驗證 textures/ 結構(跑在 uv venv)。

檢查項目:
- 必要貼圖齊全(basecolor、normal;roughness/metallic/ao 缺漏記警告)
- 解析度為 2 的次方(GPU mipmap 需求)
- normal map 平均色接近 (128, 128, 255)(切線空間特徵,抓到「不是 normal map」的檔)

用法:
    uv run scripts/validate_textures.py output/<job_id>
"""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageStat

REQUIRED = ["basecolor", "normal"]
OPTIONAL = ["roughness", "metallic", "ao", "emission"]
NORMAL_MEAN_TOLERANCE = 30  # R/G 通道與 128 的容許差
NORMAL_BLUE_MIN = 180  # B 通道平均下限


def is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def validate(job_dir: Path) -> dict:
    """回傳 {"ok": bool, "errors": [...], "warnings": [...], "checked": [...]}"""
    tex_dir = job_dir / "textures"
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []

    if not tex_dir.is_dir():
        return {"ok": False, "errors": [f"找不到 {tex_dir}"], "warnings": [], "checked": []}

    for name in REQUIRED:
        if not (tex_dir / f"{name}.png").exists():
            errors.append(f"缺必要貼圖: {name}.png")
    for name in OPTIONAL:
        if not (tex_dir / f"{name}.png").exists() and name != "emission":
            warnings.append(f"缺選用貼圖: {name}.png")

    for p in sorted(tex_dir.glob("*.png")):
        checked.append(p.name)
        with Image.open(p) as img:
            w, h = img.size
            if not (is_power_of_two(w) and is_power_of_two(h)):
                errors.append(f"{p.name}: 解析度 {w}x{h} 不是 2 的次方")
            if p.stem == "normal":
                rgb = img.convert("RGB").resize((64, 64))  # 縮小取平均,夠準又快
                mean = ImageStat.Stat(rgb).mean
                if abs(mean[0] - 128) > NORMAL_MEAN_TOLERANCE or abs(mean[1] - 128) > NORMAL_MEAN_TOLERANCE:
                    errors.append(f"normal.png 平均色 RG=({mean[0]:.0f},{mean[1]:.0f}) 偏離 128,疑非切線空間 normal map")
                if mean[2] < NORMAL_BLUE_MIN:
                    errors.append(f"normal.png B 通道平均 {mean[2]:.0f} < {NORMAL_BLUE_MIN},疑非 normal map")

    result = {"ok": not errors, "errors": errors, "warnings": warnings, "checked": checked}

    meta_path = job_dir / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        meta.setdefault("textures", {})["validation"] = result
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    status = "OK" if result["ok"] else "FAILED"
    print(f"[validate_textures] {status} — 檢查 {len(checked)} 檔")
    for e in errors:
        print(f"  錯誤: {e}")
    for w in warnings:
        print(f"  警告: {w}")
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("job_dir", type=Path, help="output/<job_id>")
    args = ap.parse_args()
    if not validate(args.job_dir)["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
