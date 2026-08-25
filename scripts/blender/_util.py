"""跑在 Blender 內的 bpy 腳本共用工具。

注意:這個模組 import bpy,只能在 Blender 的 Python 直譯器內使用,
不能在 uv venv 內 import。
"""

import sys

import bpy


def script_args() -> list[str]:
    """取得 `--` 之後留給腳本的引數。"""
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def reset_scene() -> None:
    """清成全空場景(不含預設 cube / light / camera)。"""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(filepath: str) -> list[bpy.types.Object]:
    """匯入 GLB,回傳匯入的 mesh 物件清單。"""
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=filepath)
    imported = [o for o in bpy.context.scene.objects if o not in before]
    return [o for o in imported if o.type == "MESH"]


def export_glb(filepath: str, apply_modifiers: bool = True) -> None:
    """匯出整個場景為 GLB(glTF 規範 +Y up,預設即開啟)。"""
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format="GLB",
        export_apply=apply_modifiers,
    )


def select_only(objs: list[bpy.types.Object], active: bpy.types.Object | None = None) -> None:
    """只選取指定物件,並設定 active object。"""
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or (objs[0] if objs else None)


def triangle_count(obj: bpy.types.Object) -> int:
    """以三角形數計(n-gon 換算為 n-2 個三角形)。"""
    return sum(max(len(p.vertices) - 2, 0) for p in obj.data.polygons)
