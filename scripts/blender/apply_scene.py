"""Phase 4B:把 scene.json(docs/scene-schema.md v0)套用到 Blender 場景。

供 render.py import 使用;不直接執行。
編輯器(web ?mode=editor)輸出的 scene.json 在這裡對映回 Blender:
lights / environment / camera 由 render.py 讀值傳給既有函式,
materials_override 由本模組直接改 Principled 節點——與 Three.js 端同一套
glTF 語意:factor 與貼圖「相乘」,貼圖內容不動、可還原。
"""

import json
from pathlib import Path

import bpy


def load_scene(path: Path) -> dict:
    scene = json.loads(Path(path).read_text())
    if scene.get("version") != 0:
        raise ValueError(f"不支援的 scene.json version: {scene.get('version')}")
    return scene


def _hex_to_rgba(value: str) -> tuple[float, float, float, float]:
    """#RRGGBB(sRGB)→ linear RGBA(Blender 節點色板是 linear)。"""
    v = value.lstrip("#")
    srgb = [int(v[i : i + 2], 16) / 255 for i in (0, 2, 4)]

    def to_linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (to_linear(c) for c in srgb)
    return (r, g, b, 1.0)


def _principled(mat: bpy.types.Material) -> bpy.types.ShaderNode | None:
    if not mat.use_nodes:
        return None
    return next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def _scale_input(mat: bpy.types.Material, node_input, factor: float, is_color: bool) -> None:
    """把 Principled 的某個輸入乘上 factor(glTF 的 factor × 貼圖語意)。

    輸入沒接貼圖 → 直接設值;有接貼圖 → 插入 Multiply 節點(Math 或 Mix.COLOR)。
    """
    tree = mat.node_tree
    if not node_input.links:
        if is_color:
            node_input.default_value = _hex_to_rgba(factor) if isinstance(factor, str) else factor
        else:
            node_input.default_value = factor
        return

    src = node_input.links[0].from_socket
    if is_color:
        mix = tree.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        # ShaderNodeMix 的 A/B/Result 依 data_type 有多組同名 socket,
        # inputs["A"] 會拿到 float 那組——RGBA 必須用固定索引(6/7、outputs[2])
        mix.inputs[0].default_value = 1.0  # Factor
        tree.links.new(src, mix.inputs[6])  # A (color)
        mix.inputs[7].default_value = _hex_to_rgba(factor)  # B (color)
        tree.links.new(mix.outputs[2], node_input)  # Result (color)
    else:
        math = tree.nodes.new("ShaderNodeMath")
        math.operation = "MULTIPLY"
        tree.links.new(src, math.inputs[0])
        math.inputs[1].default_value = factor
        tree.links.new(math.outputs[0], node_input)


def apply_material_overrides(overrides: dict) -> dict:
    """套用 materials_override(key = GLB 材質名)。回傳統計(寫 metadata 用)。"""
    applied: list[str] = []
    missing: list[str] = []
    for name, ov in (overrides or {}).items():
        mat = bpy.data.materials.get(name)
        node = _principled(mat) if mat else None
        if node is None:
            missing.append(name)
            continue
        if ov.get("base_color_tint") and ov["base_color_tint"].lower() != "#ffffff":
            _scale_input(mat, node.inputs["Base Color"], ov["base_color_tint"], is_color=True)
        if ov.get("roughness") is not None:
            _scale_input(mat, node.inputs["Roughness"], float(ov["roughness"]), is_color=False)
        if ov.get("metallic") is not None:
            _scale_input(mat, node.inputs["Metallic"], float(ov["metallic"]), is_color=False)
        if ov.get("emissive") and ov["emissive"].lower() != "#000000":
            node.inputs["Emission Color"].default_value = _hex_to_rgba(ov["emissive"])
            node.inputs["Emission Strength"].default_value = 1.0
        if ov.get("transmission") is not None:
            node.inputs["Transmission Weight"].default_value = float(ov["transmission"])
        if ov.get("ior") is not None:
            node.inputs["IOR"].default_value = float(ov["ior"])
        applied.append(name)
    if missing:
        print(f"[scene] 警告: materials_override 找不到材質 {missing}")
    return {"materials_overridden": applied, "materials_missing": missing}
