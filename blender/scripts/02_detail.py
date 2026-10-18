"""Step 04 detailed single-peak reef (reference: references/final-concept.png).

Fully reproducible from an empty scene:
    blender --background --python blender/scripts/02_detail.py

Outputs (relative to repo root):
    blender/scenes/02_detail.blend
    blender/renders/final/{hero,front,left,right,back,top}.png
    blender/renders/final/hierarchy.txt

Hierarchy, naming, origins and scale follow blender/MODEL_PLAN.md.
Refined organic prototypes, a packed palette atlas and authored studio lighting.
Repeated pieces are linked duplicates (shared mesh data) so they map to
InstancedMesh later.
"""

import math
import os
import random
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bmesh
import bpy
from mathutils import Matrix, Vector

# --------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------
SEED = 7

REEF_WIDTH = 3.0          # X extent of the rock mound (m)
REEF_DEPTH = 2.2          # Y extent (m)
REEF_PEAK_HEIGHT = 1.65   # the only summit; all shoulders stay below it (m)
PEAK_OFFSET = (0.28, 0.25)
MOUNTAIN_SEGMENTS = 12
# (height fraction, radius fraction): irregular cliffs alternate with ledges.
MOUNTAIN_PROFILE = [
    (0.00, 1.02), (0.12, 0.98),
    (0.29, 0.87), (0.32, 0.74),
    (0.50, 0.63), (0.53, 0.54),
    (0.72, 0.43), (0.75, 0.34),
    (0.91, 0.17),
]
SAND_RADIUS = (2.25, 1.80)

ROCK_JITTER = 0.15        # radial vertex noise on rocks (0..1)
ROCK_SUBDIV = 1           # icosphere subdivisions for rocks (1 = chunky)

# Low foothill rocks attached to the continuous mountain, never separate peaks.
# name, cx, cy, rx, ry, rz, top_cut_z
ROCKS = [
    ("Rock_Tier_001", -0.87, 0.03, 0.65, 0.57, 0.65, 0.55),
    ("Rock_Tier_002", -1.02, -0.55, 0.60, 0.45, 0.40, 0.30),
    ("Rock_Tier_003", 1.03, 0.08, 0.60, 0.53, 0.58, 0.46),
    ("Rock_Tier_004", 1.04, -0.52, 0.57, 0.42, 0.36, 0.26),
    ("Rock_Tier_005", -0.20, -0.86, 0.75, 0.40, 0.35, 0.25),
    ("Rock_Tier_006", 0.22, 0.82, 0.70, 0.41, 0.44, 0.34),
]
BOULDER_COUNT = 12
BOULDER_RADIUS = (0.09, 0.18)
BOULDER_RING = (1.35, 2.05)

# Coral placements (x, y) — z is found by ray-casting onto rocks / sand.
CORALS = {
    "Coral_BranchA": [(-1.14, -0.34), (1.20, -0.30)],
    "Coral_BranchB": [(-0.55, -0.25), (0.75, -0.60), (0.35, 0.95), (-0.95, 0.55), (1.20, 0.65), (-0.60, 0.20)],
    "Coral_Brain": [(-0.40, -0.72)],
    "Coral_TubeA": [(-0.65, -0.75), (-0.70, 0.10), (0.85, -0.85), (1.35, -0.35), (-1.25, 0.45), (1.03, 0.42), (0.30, 1.05), (-0.45, 0.90)],
    "Coral_TubeB": [(-0.95, -0.15), (0.40, -0.45), (1.25, -0.70), (-0.40, 0.70), (1.35, 0.45), (-1.35, -0.55), (0.90, 0.55), (-0.10, -0.55)],
    "Coral_Plate": [(-0.70, 0.45), (0.95, 0.25), (-0.95, -0.65), (1.10, -0.55)],
    "Coral_Bush": [(-0.30, -0.95), (0.20, -0.70), (-1.10, -0.40), (1.30, 0.35), (0.60, 0.95), (-0.15, 1.05)],
}
BRANCH_A_HEIGHT = 0.52
BRANCH_B_HEIGHT = 0.28
KELP_COUNT_PER_VARIANT = 8
KELP_RING = (1.45, 2.10)
KELP_HEIGHT = (0.30, 0.50)

DIVER_LOCATION = (-0.18, 0.08, 2.05)
DIVER_LENGTH = 0.60
DIVER_ROTATION_DEG = (-55.0, -35.0, 20.0)   # pitch head up, yaw toward camera

FISH_COUNTS = {"Fish_A": 6, "Fish_B": 5, "Fish_C": 4}
FISH_RING = (1.25, 1.95)
FISH_HEIGHT = (0.45, 1.40)

RENDER_SIZE = (1024, 768)
RENDER_SAMPLES = 64
RENDER_TARGET = (0.0, 0.0, 0.80)
# name: (azimuth_deg, elevation_deg, distance, lens_mm). azimuth 0 = front (-Y).
VIEWS = {
    "hero": (-12.0, 17.0, 6.8, 50.0),
    "front": (0.0, 12.0, 7.5, 50.0),
    "left": (-90.0, 12.0, 7.5, 50.0),
    "right": (90.0, 12.0, 7.5, 50.0),
    "back": (180.0, 12.0, 7.5, 50.0),
    "top": (0.0, 89.0, 7.5, 50.0),
}

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BLEND_PATH = os.path.join(ROOT, "blender", "scenes", "02_detail.blend")
RENDER_DIR = os.path.join(ROOT, "blender", "renders", "final")
REPORT_PATH = os.path.join(RENDER_DIR, "hierarchy.txt")

rng = random.Random(SEED)

# --------------------------------------------------------------------------
# Scene reset
# --------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def bm_to_mesh(bm, name):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return mesh


def new_object(name, mesh, parent=None, location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1)):
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    obj.scale = scale
    if parent is not None:
        obj.parent = parent
    return obj


def new_empty(name, location=(0, 0, 0), rotation=(0, 0, 0), parent=None):
    return new_object(name, None, parent=parent, location=location, rotation=rotation)


def bm_cone(bm, r1, r2, depth, segments=8, matrix=Matrix.Identity(4)):
    """Cylinder/cone with its base at z=0 (before `matrix`)."""
    lift = Matrix.Translation((0, 0, depth / 2.0))
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=segments,
        radius1=r1, radius2=r2, depth=depth, matrix=matrix @ lift,
    )


def bm_ellipsoid(bm, rx, ry, rz, subdiv=1, matrix=Matrix.Identity(4)):
    bmesh.ops.create_icosphere(
        bm, subdivisions=subdiv, radius=1.0,
        matrix=matrix @ Matrix.Diagonal((rx, ry, rz, 1.0)),
    )


def bm_box(bm, sx, sy, sz, matrix=Matrix.Identity(4)):
    """Box with its base at z=0 (before `matrix`)."""
    m = matrix @ Matrix.Translation((0, 0, sz / 2.0)) @ Matrix.Diagonal((sx, sy, sz, 1.0))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m)


def cut_plane(bm, z, keep_above):
    """Slice the mesh at height z, drop one side, fill the hole."""
    no = Vector((0, 0, -1)) if keep_above else Vector((0, 0, 1))
    res = bmesh.ops.bisect_plane(
        bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
        plane_co=Vector((0, 0, z)), plane_no=no,
        clear_outer=True, clear_inner=False,
    )
    cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if cut_edges:
        bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)


# --------------------------------------------------------------------------
# Mesh builders (every mesh has its origin at the bottom centre)
# --------------------------------------------------------------------------
def build_rock(name, rx, ry, rz, top_cut):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=ROCK_SUBDIV, radius=1.0)
    for v in bm.verts:
        v.co *= 1.0 + rng.uniform(-ROCK_JITTER, ROCK_JITTER)
    bmesh.ops.scale(bm, vec=(rx, ry, rz), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0, rz * 0.30), verts=bm.verts)
    cut_plane(bm, 0.0, keep_above=True)
    cut_plane(bm, top_cut, keep_above=False)
    return bm_to_mesh(bm, name)


def build_mountain():
    """One closed, terraced landform with exactly one summit vertex.

    Shared rings keep the mountain continuous. A separate random stream keeps
    changes to its facets independent of coral and fish instance placement.
    """
    terrain_rng = random.Random(SEED + 101)
    bm = bmesh.new()
    directions = [
        (math.tau * i / MOUNTAIN_SEGMENTS + terrain_rng.uniform(-0.06, 0.06),
         terrain_rng.uniform(0.90, 1.08), terrain_rng.uniform(-0.065, 0.065))
        for i in range(MOUNTAIN_SEGMENTS)
    ]
    rings = []
    previous_radii = None
    for level, radius in MOUNTAIN_PROFILE:
        ring = []
        radii = []
        for i, (angle, irregularity, height_offset) in enumerate(directions):
            r = radius * irregularity * terrain_rng.uniform(0.89, 1.10)
            if previous_radii is not None:
                # Every section narrows upward; no unsupported skirt at the foot.
                r = min(r, previous_radii[i] - 0.04)
            radii.append(r)
            z = level * REEF_PEAK_HEIGHT
            if level > 0:
                z += height_offset * math.sin(math.pi * level)
            ring.append(bm.verts.new((
                PEAK_OFFSET[0] * level + math.cos(angle) * REEF_WIDTH * 0.5 * r,
                PEAK_OFFSET[1] * level + math.sin(angle) * REEF_DEPTH * 0.5 * r,
                z,
            )))
        rings.append(ring)
        previous_radii = radii
    bm.faces.new(list(reversed(rings[0])))
    for level in range(len(rings) - 1):
        for i in range(MOUNTAIN_SEGMENTS):
            j = (i + 1) % MOUNTAIN_SEGMENTS
            a, b = rings[level][i], rings[level][j]
            c, d = rings[level + 1][j], rings[level + 1][i]
            # Vary diagonals to avoid a regular grid of identical cliff facets.
            if (level + i) % 2:
                bm.faces.new((a, b, d))
                bm.faces.new((b, c, d))
            else:
                bm.faces.new((a, b, c))
                bm.faces.new((a, c, d))
    summit = bm.verts.new((*PEAK_OFFSET, REEF_PEAK_HEIGHT))
    for i in range(MOUNTAIN_SEGMENTS):
        bm.faces.new((rings[-1][i], rings[-1][(i + 1) % MOUNTAIN_SEGMENTS], summit))
    return bm_to_mesh(bm, "Rock_Peak_001")


def build_sand():
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, cap_tris=True, segments=48, radius=1.0)
    bmesh.ops.scale(bm, vec=(SAND_RADIUS[0], SAND_RADIUS[1], 1.0), verts=bm.verts)
    return bm_to_mesh(bm, "Sand")


from detail_geometry import (
    C, build_branch_coral, build_brain_coral, build_tube_cluster,
    build_plate_coral, build_bush_coral, build_kelp, build_fish,
    build_diver_body, build_diver_tank, build_diver_mask, build_diver_fin,
    refine_rock, refine_sand, build_palette,
)


# --------------------------------------------------------------------------
# Build: sand + rocks
# --------------------------------------------------------------------------
scene_root = new_empty("Scene_Root")
reef_root = new_empty("Reef_Root", parent=scene_root)
sand = new_object("Sand", build_sand(), parent=scene_root)

mountain = new_object("Rock_Peak_001", build_mountain(), parent=reef_root)
mountain["bas_role"] = "single_summit_mountain"
rock_objects = [sand, mountain]
for name, cx, cy, rx, ry, rz, top in ROCKS:
    obj = new_object(name, build_rock(name, rx, ry, rz, top), parent=reef_root, location=(cx, cy, 0))
    rock_objects.append(obj)

boulder_meshes = [
    build_rock("Rock_Boulder_A", 1.0, 0.85, 0.75, 0.62),
    build_rock("Rock_Boulder_B", 1.0, 0.7, 0.9, 0.80),
]
for i in range(BOULDER_COUNT):
    variant = i % 2
    ang = 2 * math.pi * i / BOULDER_COUNT + rng.uniform(-0.2, 0.2)
    d = rng.uniform(*BOULDER_RING)
    s = rng.uniform(*BOULDER_RADIUS)
    obj = new_object(
        f"Rock_Boulder_{'AB'[variant]}_{i // 2 + 1:03d}", boulder_meshes[variant], parent=reef_root,
        location=(math.cos(ang) * d * (REEF_WIDTH / REEF_DEPTH) * 0.75, math.sin(ang) * d * 0.8, 0),
        rotation=(0, 0, rng.uniform(0, math.tau)), scale=(s, s, s),
    )
    rock_objects.append(obj)

bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()


def ground_z(x, y):
    """Highest rock/sand surface, unaffected by already placed decorations."""
    heights = [0.0]
    ray_origin = Vector((x, y, REEF_PEAK_HEIGHT + 5.0))
    ray_direction = Vector((0, 0, -1))
    for obj in rock_objects:
        inverse = obj.matrix_world.inverted()
        hit, point, _normal, _index = obj.ray_cast(
            inverse @ ray_origin,
            (inverse.to_3x3() @ ray_direction).normalized(),
        )
        if hit:
            heights.append((obj.matrix_world @ point).z)
    return max(heights)


# --------------------------------------------------------------------------
# Build: corals (shared mesh data per variant)
# --------------------------------------------------------------------------
coral_meshes = {
    "Coral_BranchA": build_branch_coral("Coral_BranchA", BRANCH_A_HEIGHT, branches=5),
    "Coral_BranchB": build_branch_coral("Coral_BranchB", BRANCH_B_HEIGHT, branches=3, sub_branches=False),
    "Coral_Brain": build_brain_coral(),
    "Coral_TubeA": build_tube_cluster("Coral_TubeA", 7, (0.20, 0.34), (0.040, 0.055), 0.11),
    "Coral_TubeB": build_tube_cluster("Coral_TubeB", 6, (0.12, 0.22), (0.045, 0.065), 0.10),
    "Coral_Plate": build_plate_coral(),
    "Coral_Bush": build_bush_coral(),
}
for key, places in CORALS.items():
    for i, (x, y) in enumerate(places):
        s = rng.uniform(0.9, 1.1)
        if key == "Coral_BranchA" and i == 1:
            s *= 0.85
        new_object(
            f"{key}_{i + 1:03d}", coral_meshes[key], parent=reef_root,
            location=(x, y, ground_z(x, y)), rotation=(0, 0, rng.uniform(0, math.tau)), scale=(s, s, s),
        )

# --------------------------------------------------------------------------
# Build: kelp
# --------------------------------------------------------------------------
kelp_meshes = {
    "Kelp_A": build_kelp("Kelp_A", 0.42, 25.0),
    "Kelp_B": build_kelp("Kelp_B", 0.34, -20.0),
}
total_kelp = KELP_COUNT_PER_VARIANT * 2
for i in range(total_kelp):
    key = "Kelp_A" if i % 2 == 0 else "Kelp_B"
    ang = 2 * math.pi * i / total_kelp + rng.uniform(-0.25, 0.25)
    d = rng.uniform(*KELP_RING)
    x, y = math.cos(ang) * d * 0.95, math.sin(ang) * d * 0.70
    s = rng.uniform(KELP_HEIGHT[0], KELP_HEIGHT[1]) / 0.40
    new_object(
        f"{key}_{i // 2 + 1:03d}", kelp_meshes[key], parent=reef_root,
        location=(x, y, ground_z(x, y)), rotation=(0, 0, rng.uniform(0, math.tau)), scale=(s, s, s),
    )

# --------------------------------------------------------------------------
# Build: diver
# --------------------------------------------------------------------------
diver = new_empty("Diver", location=DIVER_LOCATION, rotation=tuple(math.radians(a) for a in DIVER_ROTATION_DEG), parent=scene_root)
new_object("Diver_Body", build_diver_body(), parent=diver)
new_object("Diver_Tank", build_diver_tank(), parent=diver)
new_object("Diver_Mask", build_diver_mask(), parent=diver)
fin_mesh = build_diver_fin()
new_object("Diver_Fin_L", fin_mesh, parent=diver, location=(-0.41, 0.10, 0.0))
new_object("Diver_Fin_R", fin_mesh, parent=diver, location=(-0.41, -0.10, 0.0))
bpy.context.view_layer.update()
diver_points = [child.matrix_local @ Vector(corner) for child in diver.children for corner in child.bound_box]
diver_extent = max(p.x for p in diver_points) - min(p.x for p in diver_points)
diver.scale = (DIVER_LENGTH / diver_extent,) * 3

# --------------------------------------------------------------------------
# Build: fish
# --------------------------------------------------------------------------
fish_root = new_empty("Fish_Root", parent=scene_root)
fish_meshes = {
    "Fish_A": build_fish("Fish_A", 0.10, 0.30),
    "Fish_B": build_fish("Fish_B", 0.12, 0.22),
    "Fish_C": build_fish("Fish_C", 0.08, 0.24),
}
total_fish = sum(FISH_COUNTS.values())
fish_index = 0
for key, count in FISH_COUNTS.items():
    for i in range(count):
        ang = 2 * math.pi * fish_index / total_fish + rng.uniform(-0.2, 0.2)
        d = rng.uniform(*FISH_RING)
        new_object(
            f"{key}_{i + 1:03d}", fish_meshes[key], parent=fish_root,
            location=(math.cos(ang) * d, math.sin(ang) * d * 0.8, rng.uniform(*FISH_HEIGHT)),
            rotation=(0, 0, ang + math.pi / 2 + rng.uniform(-0.4, 0.4)),
        )
        fish_index += 1

# --------------------------------------------------------------------------
# Surface finish and the single palette material
# --------------------------------------------------------------------------
seen = set()
for obj in scene.objects:
    if obj.type != 'MESH' or obj.data in seen:
        continue
    seen.add(obj.data)
    if obj.name.startswith('Rock_'):
        refine_rock(obj.data, main=obj.name == 'Rock_Peak_001')
    elif obj.name == 'Sand':
        refine_sand(obj.data)

build_palette(scene, Path(ROOT) / 'blender/textures/reef_palette.png')
# Remove prototype data released by organic union operations.
for mesh in list(bpy.data.meshes):
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)

# --------------------------------------------------------------------------
# Authored render: neutral key, soft fill, cool rim, blue studio background.
# --------------------------------------------------------------------------
cam_data = bpy.data.cameras.new('Camera')
cam = new_object('Camera', cam_data)
scene.camera = cam
world = bpy.data.worlds.new('Reef_Studio')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.025, .065, .105, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
scene.world = world


def area(name, location, energy, color, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.color, data.shape, data.size = energy, color, 'DISK', size
    light = new_object(name, data, location=location)
    light.rotation_euler = (Vector((0, 0, .6)) - light.location).to_track_quat('-Z', 'Y').to_euler()


area('Key_Softbox', (-3, -4, 5), 650, (1.0, .91, .79), 4)
area('Fill_Softbox', (4, -1.5, 3), 430, (.70, .84, 1.0), 3)
area('Rim_Softbox', (0, 3.5, 4.5), 850, (.60, .85, 1.0), 3)
for engine in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        scene.render.engine = engine
        break
    except TypeError:
        pass
scene.render.threads_mode = 'FIXED'
scene.render.threads = 2
scene.eevee.taa_render_samples = RENDER_SAMPLES
scene.render.resolution_x, scene.render.resolution_y = RENDER_SIZE
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = 0
scene.view_settings.gamma = 1


def place_camera(azimuth_deg, elevation_deg, distance, lens, target=RENDER_TARGET):
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    target = Vector(target)
    cam.location = target + Vector((distance * math.cos(el) * math.sin(az),
                                   -distance * math.cos(el) * math.cos(az),
                                   distance * math.sin(el)))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam_data.lens = lens


os.makedirs(RENDER_DIR, exist_ok=True)
# --preview renders only hero; the normal command always writes all six views.
preview = '--preview' in sys.argv
for view_name, parameters in VIEWS.items():
    if preview and view_name != 'hero':
        continue
    place_camera(*parameters)
    scene.render.filepath = os.path.join(RENDER_DIR, f'{view_name}.png')
    bpy.ops.render.render(write_still=True)
if not preview:
    for label, az, el in [('diver_front', -20, 12), ('diver_back', 155, 20), ('diver_side', 75, 12)]:
        place_camera(az, el, 1.7, 60, DIVER_LOCATION)
        scene.render.filepath = os.path.join(RENDER_DIR, f'{label}.png')
        bpy.ops.render.render(write_still=True)
    import numpy as np
    width, height = 512, 384
    sheet = np.zeros((height * 2, width * 3, 4), dtype=np.float32)
    for index, label in enumerate(VIEWS):
        frame = bpy.data.images.load(os.path.join(RENDER_DIR, f'{label}.png'), check_existing=False)
        frame.scale(width, height)
        pixels = np.empty(width * height * 4, dtype=np.float32)
        frame.pixels.foreach_get(pixels)
        row, column = 1 - index // 3, index % 3
        sheet[row * height:(row + 1) * height, column * width:(column + 1) * width] = pixels.reshape(height, width, 4)
        bpy.data.images.remove(frame)
    output = bpy.data.images.new('ContactSheet', width=width * 3, height=height * 2, alpha=True)
    output.pixels.foreach_set(sheet.ravel())
    output.file_format = 'PNG'
    output.filepath_raw = os.path.join(RENDER_DIR, 'contact_sheet.png')
    output.save()
    bpy.data.images.remove(output)
place_camera(*VIEWS['hero'])
scene.render.filepath = os.path.join(RENDER_DIR, 'hero.png')

# --------------------------------------------------------------------------
# Geometry, instancing, palette, hierarchy and budget report.
# --------------------------------------------------------------------------
def tri_count(mesh):
    return sum(len(p.vertices) - 2 for p in mesh.polygons)


bpy.context.view_layer.update()
objects = [o for o in scene.objects if o.type == 'MESH']
unique = {o.data for o in objects}
groups = {}
for obj in objects:
    group = ('boulders' if obj.name.startswith('Rock_Boulder') else
             'rocks' if obj.name.startswith('Rock_') else obj.name.split('_')[0].lower())
    record = groups.setdefault(group, {'objects': 0, 'triangles': 0, 'meshes': set()})
    record['objects'] += 1
    record['triangles'] += tri_count(obj.data)
    record['meshes'].add(obj.data)
for record in groups.values():
    record['unique_triangles'] = sum(tri_count(mesh) for mesh in record.pop('meshes'))
report = {
    'blender': bpy.app.version_string, 'engine': scene.render.engine,
    'resolution': list(RENDER_SIZE), 'color_management': 'AgX / Medium High Contrast',
    'mesh_objects': len(objects), 'unique_meshes': len(unique),
    'triangles': sum(tri_count(o.data) for o in objects),
    'unique_triangles': sum(tri_count(m) for m in unique), 'groups': groups,
    'materials': len({m for o in objects for m in o.data.materials}),
    'texture': 'blender/textures/reef_palette.png',
    'preview_only': preview,
}
assert report['triangles'] < 100000, report
assert report['unique_triangles'] < 40000, report
assert report['materials'] == 1
assert all(len(m.uv_layers) == 1 for m in unique)
for name in ('Sand', 'Reef_Root', 'Fish_Root', 'Diver'):
    assert bpy.data.objects[name].parent == scene_root
for name in ('Diver_Body', 'Diver_Tank', 'Diver_Mask', 'Diver_Fin_L', 'Diver_Fin_R'):
    assert bpy.data.objects[name].parent == diver
for prefix in ('Coral_BranchA', 'Coral_BranchB', 'Coral_TubeA', 'Coral_TubeB', 'Coral_Plate', 'Coral_Bush', 'Kelp_A', 'Kelp_B', 'Fish_A', 'Fish_B', 'Fish_C'):
    variants = {o.data for o in objects if o.name.startswith(prefix + '_')}
    assert len(variants) == 1, prefix
peak_obj = bpy.data.objects['Rock_Peak_001']
maximum = max(v.co.z for v in peak_obj.data.vertices)
assert abs(maximum - REEF_PEAK_HEIGHT) < 1e-5
assert sum(abs(v.co.z - maximum) < 1e-6 for v in peak_obj.data.vertices) == 1
for obj in objects:
    if obj.name.startswith('Fish_'):
        assert tri_count(obj.data) <= 400, (obj.name, tri_count(obj.data))
report['checks'] = 'budget, single summit, hierarchy, shared variants and palette UVs passed'
Path(RENDER_DIR, 'build_report.json').write_text(json.dumps(report, indent=2) + '\n')
lines = []
def walk(obj, depth=0):
    detail = f' triangles={tri_count(obj.data)} mesh={obj.data.name}' if obj.type == 'MESH' else ''
    lines.append('  ' * depth + f'{obj.name} [{obj.type}]' + detail)
    for child in sorted(obj.children, key=lambda o: o.name):
        walk(child, depth + 1)
for obj in sorted((o for o in scene.objects if o.parent is None), key=lambda o: o.name):
    walk(obj)
Path(RENDER_DIR, 'hierarchy.txt').write_text('\n'.join(lines) + '\n')
# Packed image keeps this .blend self-contained.
os.makedirs(os.path.dirname(BLEND_PATH), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
print('DETAIL_OK', json.dumps(report))
