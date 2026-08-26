"""Phase 3 Step 3-1: 從 GLB 匯出 PBR 貼圖檔。

跑在 Blender 內(建議經 scripts/extract_textures.py 呼叫,會拆分 ORM):

    uv run scripts/run_blender.py export_textures -- --job-dir output/<job_id>

依貼圖節點連到 Principled BSDF 的輸入分類:
    Base Color / Emission → basecolor.png(sRGB)
    Normal(經 Normal Map)→ normal.png
    Metallic / Roughness(經 Separate Color)→ orm.png(R=AO, G=Roughness, B=Metallic)
輸出到 <job-dir>/textures/;ORM 通道拆分交給 venv 端(Pillow)。
"""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from _util import import_glb, reset_scene, script_args

# Principled 輸入 → 貼圖檔名
ROLE_BY_INPUT = {
    "Base Color": "basecolor",
    "Emission Color": "emission",
    "Emission": "emission",
    "Normal": "normal",
    "Metallic": "orm",
    "Roughness": "orm",
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--job-dir", type=Path, help="output/<job_id>,輸入預設 model_high.glb")
    ap.add_argument("--input", type=Path, help="輸入 GLB(預設 <job-dir>/model_high.glb)")
    ap.add_argument("--out-dir", type=Path, help="輸出目錄(預設 <job-dir>/textures)")
    args = ap.parse_args(script_args())
    if args.job_dir:
        args.input = args.input or args.job_dir / "model_high.glb"
        args.out_dir = args.out_dir or args.job_dir / "textures"
    if not (args.input and args.out_dir):
        ap.error("需要 --job-dir,或同時給 --input / --out-dir")
    if not args.input.exists():
        ap.error(f"找不到輸入檔: {args.input}")
    return args


def principled_inputs_fed(tree: bpy.types.NodeTree, tex: bpy.types.Node) -> set[str]:
    """貼圖節點(經任意中繼節點)最終連到 Principled 的哪些輸入。"""
    outgoing: dict[bpy.types.Node, list[tuple[bpy.types.Node, str]]] = {}
    for link in tree.links:
        outgoing.setdefault(link.from_node, []).append((link.to_node, link.to_socket.name))
    fed: set[str] = set()
    seen, stack = {tex}, [tex]
    while stack:
        for dst, socket in outgoing.get(stack.pop(), []):
            if dst.type == "BSDF_PRINCIPLED":
                fed.add(socket)
            elif dst not in seen:
                seen.add(dst)
                stack.append(dst)
    return fed


def save_image(image: bpy.types.Image, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.filepath_raw = str(dest)
    image.file_format = "PNG"
    image.save()


def main() -> None:
    args = parse_args()
    reset_scene()
    meshes = import_glb(str(args.input))
    if not meshes:
        sys.exit(f"GLB 內沒有 mesh: {args.input}")

    exported: dict[str, dict] = {}
    seen_mats: set[str] = set()
    for obj in meshes:
        for slot in obj.material_slots:
            mat = slot.material
            if not mat or mat.name in seen_mats or not mat.node_tree:
                continue
            seen_mats.add(mat.name)
            for n in mat.node_tree.nodes:
                if n.type != "TEX_IMAGE" or n.image is None:
                    continue
                roles = {ROLE_BY_INPUT[i] for i in principled_inputs_fed(mat.node_tree, n) if i in ROLE_BY_INPUT}
                if not roles:
                    continue
                role = roles.pop()  # 一個節點只對應一種角色(ORM 的 M/R 同檔)
                if role in exported:
                    print(f"[textures] 警告: {role} 已存在,略過重複來源 {n.image.name}")
                    continue
                dest = args.out_dir / f"{role}.png"
                save_image(n.image, dest)
                exported[role] = {
                    "file": dest.name,
                    "size_px": list(n.image.size),
                    "bytes": dest.stat().st_size,
                }
                print(f"[textures] {role}: {n.image.name} {n.image.size[0]}x{n.image.size[1]} → {dest}")

    if not exported:
        sys.exit("[textures] 模型內沒有可匯出的貼圖")
    print(f"[textures] 完成: {json.dumps(exported, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
