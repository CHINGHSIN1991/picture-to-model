"""Phase 3 Step 3-4: 高模 → 低模的貼圖烘焙(selected-to-active bake)。

跑在 Blender 內(經 scripts/run_blender.py 呼叫):

    uv run scripts/run_blender.py bake_textures -- --job-dir output/<job_id>

流程:匯入高模(保留 provider 貼圖)與 Web 低模 → 低模重新 unwrap
(乾淨 UV)→ Cycles selected-to-active 烘焙 normal / AO / diffuse(COLOR,
不含光影)/ roughness → 烘焙貼圖接回低模 Principled → 匯出 model_baked.glb。

限制:metallic 無原生 bake type,先固定 0(大多數商品可接受,金屬物件
之後以 EMIT 技巧補)。AO 存檔但不接進材質(glTF 的 occlusion 佈線需要
特殊節點群組,Web 端效益低)。
"""

import argparse
import json
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from _util import export_glb, import_glb, script_args, select_only, triangle_count
from cleanup_model import reunwrap
from render import enable_gpu

BAKE_SAMPLES = 32
DEFAULT_CAGE = 0.02  # 模型已正規化為 1 單位,0.02 ≈ 2% 投射距離


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--job-dir", type=Path, required=True, help="output/<job_id>")
    ap.add_argument("--texture-size", type=int, default=1024)
    ap.add_argument("--cage-extrusion", type=float, default=DEFAULT_CAGE)
    ap.add_argument("--output", type=Path, help="輸出 GLB(預設 <job-dir>/model_baked.glb)")
    args = ap.parse_args(script_args())
    args.output = args.output or args.job_dir / "model_baked.glb"
    for name in ("model_high.glb", "model.glb"):
        if not (args.job_dir / name).exists():
            ap.error(f"找不到 {args.job_dir / name}")
    return args


def import_single(path: Path, name: str) -> bpy.types.Object:
    meshes = import_glb(str(path))
    if len(meshes) != 1:
        sys.exit(f"{path} 應為單一 mesh(cleanup 已合併),實際 {len(meshes)} 個")
    meshes[0].name = name
    return meshes[0]


def new_bake_image(name: str, size: int, srgb: bool) -> bpy.types.Image:
    img = bpy.data.images.new(name, size, size, alpha=False)
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    return img


def setup_bake_material(web: bpy.types.Object, images: dict[str, bpy.types.Image]) -> dict[str, bpy.types.ShaderNodeTexImage]:
    """低模掛一個新材質,為每張 bake 目標圖建 Image Texture 節點。"""
    mat = bpy.data.materials.new("baked_material")
    if mat.node_tree is None:
        mat.use_nodes = True
    web.data.materials.clear()
    web.data.materials.append(mat)
    nodes = {}
    for key, img in images.items():
        node = mat.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = img
        node.name = f"bake_{key}"
        nodes[key] = node
    return nodes


def bake_pass(web_nodes: dict, key: str, bake_type: str, **kw) -> float:
    """執行一個 bake pass(高模已 selected、低模 active)。回傳耗時。"""
    mat = bpy.context.active_object.active_material
    for node in mat.node_tree.nodes:
        node.select = False
    target = web_nodes[key]
    target.select = True
    mat.node_tree.nodes.active = target  # bake 寫入 active image node
    t0 = time.time()
    bpy.ops.object.bake(type=bake_type, use_selected_to_active=True, **kw)
    elapsed = round(time.time() - t0, 1)
    print(f"[bake] {key} ({bake_type}) 完成 {elapsed}s")
    return elapsed


def wire_material(mat: bpy.types.Material, nodes: dict) -> None:
    """烘焙貼圖接回 Principled(依 Step 2-3 的標準佈線)。"""
    tree = mat.node_tree
    bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    tree.links.new(nodes["basecolor"].outputs["Color"], bsdf.inputs["Base Color"])
    tree.links.new(nodes["roughness"].outputs["Color"], bsdf.inputs["Roughness"])
    normal_map = tree.nodes.new("ShaderNodeNormalMap")
    tree.links.new(nodes["normal"].outputs["Color"], normal_map.inputs["Color"])
    tree.links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Metallic"].default_value = 0.0  # 限制:見模組 docstring
    # AO 只存檔不接線
    nodes["ao"].select = False


def main() -> None:
    args = parse_args()
    t0 = time.time()

    bpy.ops.wm.read_factory_settings(use_empty=True)
    high = import_single(args.job_dir / "model_high.glb", "high")
    web = import_single(args.job_dir / "model.glb", "web")

    reunwrap(web)
    print("[bake] Web 模型已重新 unwrap")

    size = args.texture_size
    images = {
        "basecolor": new_bake_image("bake_basecolor", size, srgb=True),
        "normal": new_bake_image("bake_normal", size, srgb=False),
        "ao": new_bake_image("bake_ao", size, srgb=False),
        "roughness": new_bake_image("bake_roughness", size, srgb=False),
    }
    nodes = setup_bake_material(web, images)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    device = enable_gpu()
    scene.cycles.samples = BAKE_SAMPLES

    select_only([high, web], active=web)  # 高模 selected、低模 active
    cage = {"cage_extrusion": args.cage_extrusion}
    timings = {
        "normal": bake_pass(nodes, "normal", "NORMAL", **cage),
        "ao": bake_pass(nodes, "ao", "AO", **cage),
        "basecolor": bake_pass(nodes, "basecolor", "DIFFUSE", pass_filter={"COLOR"}, **cage),
        "roughness": bake_pass(nodes, "roughness", "ROUGHNESS", **cage),
    }

    tex_dir = args.job_dir / "textures"
    tex_dir.mkdir(exist_ok=True)
    saved = {}
    for key, img in images.items():
        dest = tex_dir / f"baked_{key}.png"
        img.filepath_raw = str(dest)
        img.file_format = "PNG"
        img.save()
        saved[key] = {"file": dest.name, "bytes": dest.stat().st_size}

    wire_material(web.active_material, nodes)
    bpy.data.objects.remove(high, do_unlink=True)  # 只匯出低模
    select_only([web])
    export_glb(str(args.output))

    stats = {
        "device": device,
        "texture_size": size,
        "cage_extrusion": args.cage_extrusion,
        "samples": BAKE_SAMPLES,
        "tris_web": triangle_count(web),
        "bake_sec": timings,
        "files": saved,
        "baked_glb_bytes": args.output.stat().st_size,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    meta_path = args.job_dir / "metadata.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta["bake"] = stats
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"[bake] 完成 ({stats['elapsed_sec']}s, {device}) → {args.output}")


if __name__ == "__main__":
    main()
