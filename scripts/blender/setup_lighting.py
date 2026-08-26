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


# 三點打光預設值(= scene.json schema 的 lights 預設;size 依角色固定)
DEFAULT_LIGHTS = [
    {"id": "key", "azimuth": 75, "elevation": 45, "power": 400},
    {"id": "fill", "azimuth": -30, "elevation": 20, "power": 130},
    {"id": "rim", "azimuth": 200, "elevation": 40, "power": 250},
]
_LIGHT_SIZE = {"key": 2.0, "fill": 3.0, "rim": 2.0}


def build_lighting(
    hdri_path: Path | None = None,
    hdri_strength: float = 0.4,
    azimuth_offset: float = 0.0,
    lights: list[dict] | None = None,
    hdri_rotation: float = 0.0,
) -> dict:
    """三點打光 + HDRI 環境光。回傳統計(寫 metadata 用)。

    azimuth_offset: 整組光源(含 HDRI)繞 Z 軸旋轉的角度。
    固定相機、旋轉打光渲染多張,可檢驗貼圖是否為真 PBR
    (高光跟著光走)或烤死的光影(高光黏在表面)。
    lights: scene.json 的 lights[](id/azimuth/elevation/power),None 用預設三點打光。
    hdri_rotation: scene.json 的 environment.rotation——只轉 HDRI、不動燈
    (與 azimuth_offset 疊加)。
    """
    # 相機預設在方位角 30°(見 setup_camera),Key 放相機同側偏外
    light_names = []
    for l in lights if lights is not None else DEFAULT_LIGHTS:
        name = f"{l['id'].capitalize()}Light"
        _add_area_light(
            name,
            azimuth=l["azimuth"] + azimuth_offset,
            elevation=l["elevation"],
            energy=l["power"],
            size=_LIGHT_SIZE.get(l["id"], 2.0),
        )
        light_names.append(name)

    world = bpy.data.worlds.new("StudioWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    hdri = hdri_path if hdri_path is not None else DEFAULT_HDRI
    used_hdri = False
    if hdri and Path(hdri).exists():
        env = world.node_tree.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(str(hdri))
        env_rotation = azimuth_offset + hdri_rotation  # 評估用整組旋轉 + 編輯器 HDRI 旋轉
        if env_rotation:
            coord = world.node_tree.nodes.new("ShaderNodeTexCoord")
            mapping = world.node_tree.nodes.new("ShaderNodeMapping")
            mapping.inputs["Rotation"].default_value[2] = math.radians(env_rotation)
            world.node_tree.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
            world.node_tree.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
        world.node_tree.links.new(env.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = hdri_strength
        used_hdri = True
    else:
        bg.inputs["Color"].default_value = (0.9, 0.9, 0.9, 1.0)
        bg.inputs["Strength"].default_value = hdri_strength
        print(f"[lighting] 找不到 HDRI({hdri}),改用均勻灰色環境光")
    return {"lights": light_names, "hdri": Path(hdri).name if used_hdri else None}
