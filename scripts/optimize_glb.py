"""Stage optimize(D-1):Web 版 GLB 壓縮(跑在 uv venv,呼叫 web/ 的 gltf-transform)。

pipeline 第 6 站,在 textures 之後、render(poster)之前。壓縮永遠放最後:壓完不再改內容。
幾何 meshopt(預設;viewer 的 useGlb.ts 已掛 MeshoptDecoder)或 Draco(需另掛 DRACOLoader),
貼圖 WebP。鎖 --simplify false(面數歸 Blender decimate 管)、--palette false
(材質名是 scene.json materials_override 的 key,不能被合併改名)。

輸出:<job>/web/model.glb(與 model_baked.glb,若存在);統計寫 metadata.json 的 optimize 欄位。

用法:
    uv run scripts/optimize_glb.py output/<job_id>
    uv run scripts/optimize_glb.py output/<job_id> --compress draco
    uv run scripts/optimize_glb.py in.glb out.glb                # 單檔模式
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
DEFAULT_INPUTS = ("model.glb", "model_baked.glb")
COMPRESSORS = ("meshopt", "draco")
TEXTURE_FORMATS = ("webp", "avif", "png", "jpeg", "false")


def find_gltf_transform() -> list[str]:
    local = WEB_DIR / "node_modules" / ".bin" / "gltf-transform"
    if local.exists():
        return [str(local)]
    if shutil.which("gltf-transform"):
        return ["gltf-transform"]
    if shutil.which("npm"):
        return ["npm", "exec", "--prefix", str(WEB_DIR), "--", "gltf-transform"]
    raise RuntimeError("找不到 gltf-transform:請先 `cd web && npm install`(@gltf-transform/cli 在 devDependencies)")


def tool_version(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run([*cmd, "--version"], capture_output=True, text=True, timeout=60)
        return out.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def optimize_glb(src: Path, dst: Path, compress: str = "meshopt", texture: str = "webp",
                 cmd: list[str] | None = None) -> dict:
    """單檔壓縮,回傳前後大小統計。失敗 raise RuntimeError。"""
    if compress not in COMPRESSORS:
        raise ValueError(f"compress 需為 {COMPRESSORS}")
    cmd = cmd or find_gltf_transform()
    dst.parent.mkdir(parents=True, exist_ok=True)
    args = [*cmd, "optimize", str(src), str(dst),
            "--compress", compress, "--texture-compress", texture,
            "--simplify", "false", "--palette", "false"]
    t0 = time.time()
    proc = subprocess.run(args, capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0 or not dst.exists():
        tail = (proc.stderr or proc.stdout).strip()[-800:]
        raise RuntimeError(f"gltf-transform optimize 失敗 (exit {proc.returncode}) {src.name}:\n{tail}")
    before, after = src.stat().st_size, dst.stat().st_size
    return {
        "input": src.name,
        "output": str(dst),
        "input_bytes": before,
        "output_bytes": after,
        "ratio": round(after / before, 3) if before else None,
        "saved_pct": round((1 - after / before) * 100, 1) if before else None,
        "elapsed_sec": round(time.time() - t0, 1),
    }


def optimize_job(job_dir: Path, compress: str = "meshopt", texture: str = "webp",
                 inputs: tuple[str, ...] = DEFAULT_INPUTS) -> dict:
    """壓縮 job 內的 Web 版 GLB 到 <job>/web/,統計寫進 metadata.json。"""
    t0 = time.time()
    cmd = find_gltf_transform()
    web_dir = job_dir / "web"
    files: dict[str, dict] = {}
    for name in inputs:
        src = job_dir / name
        if not src.exists():
            continue
        stat = optimize_glb(src, web_dir / name, compress=compress, texture=texture, cmd=cmd)
        stat["output"] = str(Path("web") / name)
        files[name] = stat
        print(f"[optimize] {name}: {stat['input_bytes']/1e6:.2f}MB → {stat['output_bytes']/1e6:.2f}MB"
              f" (−{stat['saved_pct']}%) {stat['elapsed_sec']}s")
    if not files:
        raise RuntimeError(f"{job_dir} 內沒有 {', '.join(inputs)} 可壓縮")

    meta = {
        "tool": "gltf-transform",
        "tool_version": tool_version(cmd),
        "compressor": compress,
        "texture_format": texture,
        "params": {"simplify": False, "palette": False},
        "viewer_decoder": "MeshoptDecoder(three 內建)" if compress == "meshopt" else "DRACOLoader(需託管 WASM)",
        "files": files,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    if compress == "draco":
        print("[optimize] ⚠ Draco 需 viewer 掛 DRACOLoader;目前 useGlb.ts 只掛 MeshoptDecoder")
    meta_path = job_dir / "metadata.json"
    full = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    full["optimize"] = meta
    meta_path.write_text(json.dumps(full, ensure_ascii=False, indent=2))
    return meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", type=Path, help="output/<job_id> 或單一 .glb")
    ap.add_argument("output", type=Path, nargs="?", help="單檔模式的輸出路徑")
    ap.add_argument("--compress", choices=COMPRESSORS, default="meshopt")
    ap.add_argument("--texture-compress", choices=TEXTURE_FORMATS, default="webp")
    args = ap.parse_args()

    if args.target.is_dir():
        optimize_job(args.target, compress=args.compress, texture=args.texture_compress)
    elif args.target.suffix.lower() in (".glb", ".gltf"):
        if not args.output:
            ap.error("單檔模式需要輸出路徑")
        stat = optimize_glb(args.target, args.output, compress=args.compress, texture=args.texture_compress)
        print(json.dumps(stat, ensure_ascii=False, indent=2))
    else:
        sys.exit(f"不是 job 目錄也不是 GLB: {args.target}")


if __name__ == "__main__":
    main()
