"""Phase 2 Step 2-1: Blender headless 包裝器(跑在 uv venv)。

用法:
    uv run scripts/run_blender.py cleanup_model -- --job-dir output/<job_id>
    uv run scripts/run_blender.py <scripts/blender/ 下的腳本名或路徑> -- <腳本引數...>

Blender 執行檔尋找順序:.env 的 BLENDER_BIN → PATH 上的 blender
→ /Applications/Blender.app。
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

BLENDER_SCRIPTS_DIR = Path(__file__).parent / "blender"
DEFAULT_TIMEOUT = 1800  # 秒

MACOS_APP_BIN = "/Applications/Blender.app/Contents/MacOS/Blender"


def find_blender() -> str:
    load_dotenv()
    candidates = [os.getenv("BLENDER_BIN"), shutil.which("blender"), MACOS_APP_BIN]
    for c in candidates:
        if c and Path(c).exists():
            return c
    sys.exit("找不到 Blender 執行檔:請在 .env 設定 BLENDER_BIN,或將 blender 加入 PATH")


def resolve_script(name_or_path: str) -> Path:
    """接受腳本名(cleanup_model)、檔名(cleanup_model.py)或完整路徑。"""
    p = Path(name_or_path)
    if p.exists():
        return p
    candidate = BLENDER_SCRIPTS_DIR / (name_or_path if name_or_path.endswith(".py") else f"{name_or_path}.py")
    if candidate.exists():
        return candidate
    sys.exit(f"找不到 bpy 腳本: {name_or_path}(scripts/blender/ 下也沒有)")


def run(script: str | Path, script_args: list[str] | None = None, timeout: int = DEFAULT_TIMEOUT) -> int:
    """執行一個 bpy 腳本,stdout/stderr 直接串流到終端,回傳 exit code。

    Pipeline 的其他步驟都應經過這個函式呼叫 Blender。
    """
    blender = find_blender()
    script_path = resolve_script(str(script))
    cmd = [blender, "--background", "--python", str(script_path)]
    if script_args:
        cmd += ["--", *script_args]
    print(f"[run_blender] $ {' '.join(cmd)}", flush=True)
    try:
        proc = subprocess.run(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"[run_blender] 超過 {timeout}s,已中止", file=sys.stderr)
        return 124
    if proc.returncode != 0:
        print(f"[run_blender] Blender 以 exit code {proc.returncode} 結束", file=sys.stderr)
    return proc.returncode


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("script", help="bpy 腳本名或路徑(如 cleanup_model)")
    ap.add_argument("script_args", nargs=argparse.REMAINDER, help="`--` 之後傳給腳本的引數")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = ap.parse_args()

    passthrough = args.script_args
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]
    sys.exit(run(args.script, passthrough, timeout=args.timeout))


if __name__ == "__main__":
    main()
