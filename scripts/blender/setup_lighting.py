"""Phase 2 Step 2-4: 程式化攝影棚打光(三點打光 + HDRI 環境)。

供 render.py import 使用;不直接執行。
以程式建光取代手動 studio.blend,確保所有商品圖打光一致且可版本控制。
"""

import math
from pathlib import Path

import bpy
from mathutils import Vector

# repo 根目錄的 assets/(CC0,Poly Haven studio_small_08)
ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
DEFAULT_HDRI = ASSETS_DIR / "studio_small_08_1k.hdr"


def spherical(azimuth_deg: float, elevation_deg: float, distance: float) -> tuple[float, float, float]:
    """球座標 → 直角座標。方位角 0° = 正前方(-Y),仰角 0° = 水平。"""
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    return (
        distance * math.cos(el) * math.sin(az),
        -distance * math.cos(el) * math.cos(az),
        distance * math.sin(el),
    )


def aim_at(obj: bpy.types.Object, target: Vector) -> None:
    """把物件的 -Z 軸指向 target(燈與相機通用)。"""
    direction = target - Vector(obj.location)
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _add_area_light(name: str, azimuth: float, elevation: float, energy: float, size: float, distance: float = 4.0) -> bpy.types.Object:
    data = bpy.data.lights.new(name, type="AREA")
    data.energy = energy
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = spherical(azimuth, elevation, distance)
    aim_at(obj, Vector((0.0, 0.0, 0.0)))
    return obj


def build_lighting(
    hdri_path: Path | None = None,
    hdri_strength: float = 0.4,
    azimuth_offset: float = 0.0,
) -> dict:
    """三點打光 + HDRI 環境光。回傳統計(寫 metadata 用)。

    azimuth_offset: 整組光源(含 HDRI)繞 Z 軸旋轉的角度。
    固定相機、旋轉打光渲染多張,可檢驗貼圖是否為真 PBR
    (高光跟著光走)或烤死的光影(高光黏在表面)。
    """
    # 相機預設在方位角 30°(見 setup_camera),Key 放相機同側偏外
    _add_area_light("KeyLight", azimuth=75 + azimuth_offset, elevation=45, energy=400, size=2.0)
    _add_area_light("FillLight", azimuth=-30 + azimuth_offset, elevation=20, energy=130, size=3.0)
    _add_area_light("RimLight", azimuth=200 + azimuth_offset, elevation=40, energy=250, size=2.0)

    world = bpy.data.worlds.new("StudioWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    hdri = hdri_path if hdri_path is not None else DEFAULT_HDRI
    used_hdri = False
    if hdri and Path(hdri).exists():
        env = world.node_tree.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(str(hdri))
        if azimuth_offset:  # HDRI 跟著整組光源一起轉
            coord = world.node_tree.nodes.new("ShaderNodeTexCoord")
            mapping = world.node_tree.nodes.new("ShaderNodeMapping")
            mapping.inputs["Rotation"].default_value[2] = math.radians(azimuth_offset)
            world.node_tree.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
            world.node_tree.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
        world.node_tree.links.new(env.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = hdri_strength
        used_hdri = True
    else:
        bg.inputs["Color"].default_value = (0.9, 0.9, 0.9, 1.0)
        bg.inputs["Strength"].default_value = hdri_strength
        print(f"[lighting] 找不到 HDRI({hdri}),改用均勻灰色環境光")
    return {"lights": ["KeyLight", "FillLight", "RimLight"], "hdri": Path(hdri).name if used_hdri else None}
