"""Phase 2 Step 2-4: 自動取景相機。

供 render.py import 使用;不直接執行。
模型已在 cleanup 正規化(置中原點、最長邊 1 單位),
相機以固定球座標構圖,距離依 bounding box 與 FOV 計算確保完整入鏡。
"""

import math

import bpy
from mathutils import Vector

from setup_lighting import aim_at, spherical


def world_bounds(objs: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    """所有物件的世界座標 bounding box(min, max)。"""
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for obj in objs:
        for corner in obj.bound_box:
            p = obj.matrix_world @ Vector(corner)
            lo = Vector(map(min, lo, p))
            hi = Vector(map(max, hi, p))
    return lo, hi


def frame_camera(
    targets: list[bpy.types.Object],
    azimuth: float = 30.0,
    elevation: float = 18.0,
    margin: float = 1.4,
    lens_mm: float = 50.0,
) -> bpy.types.Object:
    """建立 ProductCamera 並對準模型,依 bounding box 自動調整距離。"""
    data = bpy.data.cameras.new("ProductCamera")
    data.lens = lens_mm
    cam = bpy.data.objects.new("ProductCamera", data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    lo, hi = world_bounds(targets)
    center = (lo + hi) / 2
    max_dim = max(hi - lo)
    # 以較窄的視角軸為準(正方形輸出時兩軸相同)
    fov = min(data.angle_x, data.angle_y)
    distance = (max_dim / 2) / math.tan(fov / 2) * margin

    cam.location = center + Vector(spherical(azimuth, elevation, distance))
    aim_at(cam, center)
    return cam
