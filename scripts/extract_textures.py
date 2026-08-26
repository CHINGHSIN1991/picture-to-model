"""Phase 3 Step 3-1: 抽出標準化 PBR 貼圖結構(跑在 uv venv)。

呼叫 Blender export_textures.py 取得 basecolor/normal/orm,再以 Pillow
把 ORM 拆成獨立灰階檔,形成標準結構:

    output/<job_id>/textures/
    ├── basecolor.png   # sRGB
    ├── normal.png      # Non-Color
    ├── roughness.png   # Non-Color, 灰階(ORM G 通道)
    ├── metallic.png    # Non-Color, 灰階(ORM B 通道)
    └── ao.png          # Non-Color, 灰階(ORM R 通道)

用法:
    uv run scripts/extract_textures.py output/<job_id>
"""

import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image

from run_blender import run

# ORM 通道 → 檔名(glTF 慣例:R=AO, G=Roughness, B=Metallic)
ORM_CHANNELS = {"R": "ao", "G": "roughness", "B": "metallic"}


def split_orm(orm_path: Path) -> dict[str, dict]:
    img = Image.open(orm_path).convert("RGB")
    out: dict[str, dict] = {}
    for channel, name in ORM_CHANNELS.items():
        dest = orm_path.parent / f"{name}.png"
        img.getchannel(channel).save(dest)
        out[name] = {"file": dest.name, "size_px": list(img.size), "bytes": dest.stat().st_size}
    orm_path.unlink()  # 拆完即刪,保持結構乾淨
    return out


def extract_textures(job_dir: Path) -> dict:
    """抽貼圖 + 拆 ORM,寫 metadata textures 欄位,回傳統計。"""
    t0 = time.time()
    rc = run("export_textures", ["--job-dir", str(job_dir)])
    if rc != 0:
        raise RuntimeError(f"Blender export_textures 失敗 (exit code {rc})")

    tex_dir = job_dir / "textures"
    files: dict[str, dict] = {}
    for p in sorted(tex_dir.glob("*.png")):
        with Image.open(p) as img:
            files[p.stem] = {"file": p.name, "size_px": list(img.size), "bytes": p.stat().st_size}

    orm = tex_dir / "orm.png"
    if orm.exists():
        files.pop("orm", None)
        files.update(split_orm(orm))

    stats = {
        "source": "provider",  # 目前貼圖皆來自 AI provider;之後 bake/generated 會覆寫
        "files": files,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    meta_path = job_dir / "metadata.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta["textures"] = stats
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"[extract_textures] 完成 ({stats['elapsed_sec']}s): {', '.join(sorted(files))}")
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("job_dir", type=Path, help="output/<job_id>")
    args = ap.parse_args()
    try:
        extract_textures(args.job_dir)
    except RuntimeError as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
