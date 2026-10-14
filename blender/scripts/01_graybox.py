"""Step 03 graybox: coral reef diorama (reference: references/final-concept.png).

Fully reproducible from an empty scene:
    blender --background --python blender/scripts/01_graybox.py

Outputs (relative to repo root):
    blender/scenes/01_graybox.blend
    blender/renders/graybox/{hero,front,left,right,back,top}.png
    blender/renders/graybox/hierarchy.txt

Hierarchy, naming, origins and scale follow blender/MODEL_PLAN.md.
No materials, no subdivision: every object is a simple primitive placeholder.
Repeated pieces are linked duplicates (shared mesh data) so they map to
InstancedMesh later.
"""

import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

# --------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------
SEED = 7

REEF_WIDTH = 3.0          # X extent of the rock mound (m)
REEF_DEPTH = 2.2          # Y extent (m)
REEF_PEAK_HEIGHT = 1.45   # top of Rock_Peak (m)
SAND_RADIUS = (3.2, 2.5)  # sand disk X / Y radius (m)

ROCK_JITTER = 0.15        # radial vertex noise on rocks (0..1)
ROCK_SUBDIV = 1           # icosphere subdivisions for rocks (1 = chunky)

# Rock layout: name, cx, cy, rx, ry, rz, top_cut_z
ROCKS = [
    # centre peak cluster (reference: peak sits right of centre)
    ("Rock_Peak_001", 0.30, 0.25, 0.55, 0.50, 1.30, REEF_PEAK_HEIGHT),
    ("Rock_Tier_001", 0.25, 0.05, 0.85, 0.70, 1.00, 0.95),
    # left mound (tall, carries the big branch coral)
    ("Rock_Tier_002", -1.05, 0.15, 0.62, 0.55, 0.85, 0.78),
    ("Rock_Tier_003", -0.85, -0.55, 0.55, 0.45, 0.50, 0.42),
    # right mound
    ("Rock_Tier_004", 1.05, 0.20, 0.58, 0.50, 0.80, 0.70),
    ("Rock_Tier_005", 1.15, -0.50, 0.50, 0.40, 0.45, 0.38),
    # front terrace
    ("Rock_Tier_006", 0.10, -0.70, 0.60, 0.40, 0.50, 0.40),
    ("Rock_Tier_007", -0.40, -0.30, 0.50, 0.40, 0.70, 0.62),
    ("Rock_Tier_008", 0.70, -0.35, 0.50, 0.40, 0.65, 0.55),
    # back
    ("Rock_Tier_009", -0.30, 0.75, 0.55, 0.45, 0.60, 0.50),
    ("Rock_Tier_010", 0.90, 0.80, 0.50, 0.40, 0.55, 0.45),
]
BOULDER_COUNT = 12
BOULDER_RADIUS = (0.09, 0.18)
BOULDER_RING = (1.35, 2.05)

# Coral placements (x, y) — z is found by ray-casting onto rocks / sand.
CORALS = {
    "Coral_BranchA": [(-1.15, -0.05), (1.15, 0.05)],
    "Coral_BranchB": [(-0.55, -0.25), (0.75, -0.60), (0.35, 0.95), (-0.95, 0.55), (1.20, 0.75), (0.05, 0.30)],
    "Coral_Brain": [(0.05, -0.80)],
    "Coral_TubeA": [(-0.65, -0.75), (-0.25, 0.20), (0.85, -0.85), (1.45, -0.35), (-1.35, 0.45), (0.55, 0.40), (0.30, 1.05), (-0.45, 1.05)],
    "Coral_TubeB": [(-0.95, -0.15), (0.40, -0.35), (1.25, -0.70), (-0.40, 0.70), (1.45, 0.45), (-1.45, -0.55), (0.90, 0.55), (-0.10, -0.45)],
    "Coral_Plate": [(-0.70, 0.45), (0.95, 0.25), (-0.95, -0.60), (1.10, -0.55)],
    "Coral_Bush": [(-0.30, -0.95), (0.20, 0.05), (-1.10, -0.40), (1.30, 0.35), (0.60, 1.00), (-0.15, 1.15)],
}
KELP_COUNT_PER_VARIANT = 8
KELP_RING = (1.45, 2.10)
KELP_HEIGHT = (0.30, 0.50)

DIVER_LOCATION = (-0.15, 0.10, 1.85)
DIVER_LENGTH = 0.60
DIVER_ROTATION_DEG = (0.0, -35.0, 20.0)   # pitch head up, yaw toward camera

FISH_COUNTS = {"Fish_A": 6, "Fish_B": 5, "Fish_C": 4}
FISH_RING = (1.25, 1.95)
FISH_HEIGHT = (0.45, 1.40)

RENDER_SIZE = (1024, 768)
RENDER_TARGET = (0.0, 0.0, 0.65)
# name: (azimuth_deg, elevation_deg, distance, lens_mm). azimuth 0 = front (-Y).
VIEWS = {
    "hero": (-25.0, 22.0, 6.2, 45.0),
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
BLEND_PATH = os.path.join(ROOT, "blender", "scenes", "01_graybox.blend")
RENDER_DIR = os.path.join(ROOT, "blender", "renders", "graybox")
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


def build_sand():
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, cap_tris=True, segments=48, radius=1.0)
    bmesh.ops.scale(bm, vec=(SAND_RADIUS[0], SAND_RADIUS[1], 1.0), verts=bm.verts)
    return bm_to_mesh(bm, "Sand")


def build_branch_coral(name, height, branches, sub_branches=True):
    """Trunk + angled branches + small sub-branches. Height ~ `height`."""
    bm = bmesh.new()
    trunk_h = height * 0.40
    bm_cone(bm, 0.06, 0.045, trunk_h, segments=8)
    for i in range(branches):
        yaw = math.radians(360.0 / branches * i + rng.uniform(-15, 15))
        tilt = math.radians(rng.uniform(30, 45))
        rot = Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(tilt, 4, "Y")
        base = Matrix.Translation((0, 0, trunk_h * 0.9)) @ rot
        blen = height * 0.50
        bm_cone(bm, 0.040, 0.028, blen, segments=6, matrix=base)
        if sub_branches:
            tip = base @ Matrix.Translation((0, 0, blen * 0.95))
            for j in range(2):
                yaw2 = math.radians(90 + 180 * j + rng.uniform(-20, 20))
                rot2 = Matrix.Rotation(yaw2, 4, "Z") @ Matrix.Rotation(math.radians(35), 4, "Y")
                bm_cone(bm, 0.020, 0.014, height * 0.25, segments=6, matrix=tip @ rot2)
    return bm_to_mesh(bm, name)


def build_brain_coral():
    bm = bmesh.new()
    bm_ellipsoid(bm, 0.21, 0.19, 0.15, subdiv=2)
    for v in bm.verts:
        v.co *= 1.0 + rng.uniform(-0.04, 0.04)
    bmesh.ops.translate(bm, vec=(0, 0, 0.10), verts=bm.verts)
    cut_plane(bm, 0.0, keep_above=True)
    return bm_to_mesh(bm, "Coral_Brain")


def build_tube_cluster(name, count, height_range, radius_range, spread):
    bm = bmesh.new()
    for i in range(count):
        ang = 2 * math.pi * i / count + rng.uniform(-0.3, 0.3)
        d = rng.uniform(0.0, spread)
        r = rng.uniform(*radius_range)
        h = rng.uniform(*height_range)
        tilt = math.radians(rng.uniform(-12, 12))
        m = (Matrix.Translation((math.cos(ang) * d, math.sin(ang) * d, 0))
             @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(tilt, 4, "Y"))
        bm_cone(bm, r, r * 0.9, h, segments=8, matrix=m)
    return bm_to_mesh(bm, name)


def build_plate_coral():
    bm = bmesh.new()
    bm_cone(bm, 0.035, 0.035, 0.05, segments=8)                       # stem
    bm_cone(bm, 0.05, 0.23, 0.12, segments=12, matrix=Matrix.Translation((0, 0, 0.05)))
    return bm_to_mesh(bm, "Coral_Plate")


def build_bush_coral():
    bm = bmesh.new()
    for i in range(5):
        ang = 2 * math.pi * i / 5
        m = Matrix.Translation((math.cos(ang) * 0.07, math.sin(ang) * 0.07, 0.07))
        bm_ellipsoid(bm, 0.08, 0.08, 0.09, subdiv=1, matrix=m)
    bm_ellipsoid(bm, 0.09, 0.09, 0.10, subdiv=1, matrix=Matrix.Translation((0, 0, 0.14)))
    cut_plane(bm, 0.0, keep_above=True)
    return bm_to_mesh(bm, "Coral_Bush")


def build_kelp(name, height, lean_deg):
    """Thin blade with a gentle S lean. Origin at the root."""
    bm = bmesh.new()
    segs = 4
    seg_h = height / segs
    for i in range(segs):
        lean = math.radians(lean_deg * math.sin(i / segs * math.pi))
        m = Matrix.Translation((0, 0, i * seg_h)) @ Matrix.Rotation(lean, 4, "X")
        bm_box(bm, 0.06 - i * 0.008, 0.02, seg_h * 1.05, matrix=m)
    return bm_to_mesh(bm, name)


def build_fish(name, length, body_ratio):
    bm = bmesh.new()
    L = length
    bm_ellipsoid(bm, L * 0.40, L * 0.14, L * body_ratio, subdiv=1)
    tail = Matrix.Translation((-L * 0.40, 0, 0)) @ Matrix.Rotation(math.radians(-90), 4, "Y")
    bm_cone(bm, 0.0, L * 0.18, L * 0.22, segments=4, matrix=tail @ Matrix.Diagonal((1.0, 0.2, 1.0, 1.0)))
    return bm_to_mesh(bm, name)


def build_diver_body():
    """Torso + head + arms + legs along +X (head direction). Origin at chest."""
    bm = bmesh.new()
    bm_ellipsoid(bm, 0.14, 0.09, 0.075, subdiv=2)                                   # torso
    bm_ellipsoid(bm, 0.065, 0.06, 0.06, subdiv=1, matrix=Matrix.Translation((0.19, 0, 0.02)))  # head
    limb = Matrix.Rotation(math.radians(90), 4, "Y")                                # cone +z -> +x
    for side in (-1, 1):
        arm = (Matrix.Translation((0.08, side * 0.085, 0.0))
               @ Matrix.Rotation(math.radians(side * 55), 4, "Z") @ limb)
        bm_cone(bm, 0.03, 0.025, 0.24, segments=6, matrix=arm)
        leg = (Matrix.Translation((-0.12, side * 0.045, 0.0))
               @ Matrix.Rotation(math.radians(180 - side * 12), 4, "Z") @ limb)
        bm_cone(bm, 0.04, 0.03, 0.30, segments=6, matrix=leg)
    return bm_to_mesh(bm, "Diver_Body")


def build_diver_tank():
    bm = bmesh.new()
    m = Matrix.Translation((0.10, 0, 0.07)) @ Matrix.Rotation(math.radians(-90), 4, "Y")
    bm_cone(bm, 0.045, 0.045, 0.22, segments=10, matrix=m)
    return bm_to_mesh(bm, "Diver_Tank")


def build_diver_mask():
    bm = bmesh.new()
    bm_box(bm, 0.03, 0.09, 0.04, matrix=Matrix.Translation((0.24, 0, -0.02)))
    return bm_to_mesh(bm, "Diver_Mask")


def build_diver_fin():
    bm = bmesh.new()
    bm_box(bm, 0.16, 0.07, 0.015, matrix=Matrix.Translation((-0.08, 0, 0)))
    return bm_to_mesh(bm, "Diver_Fin")


# --------------------------------------------------------------------------
# Build: sand + rocks
# --------------------------------------------------------------------------
reef_root = new_empty("Reef_Root")
sand = new_object("Sand", build_sand())

rock_objects = [sand]
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
    """Height of the rock / sand surface under (x, y)."""
    hit, loc, _n, _i, obj, _m = scene.ray_cast(depsgraph, Vector((x, y, 5.0)), Vector((0, 0, -1)))
    if hit and obj in rock_objects:
        return loc.z
    return 0.0


# --------------------------------------------------------------------------
# Build: corals (shared mesh data per variant)
# --------------------------------------------------------------------------
coral_meshes = {
    "Coral_BranchA": build_branch_coral("Coral_BranchA", 0.78, branches=5),
    "Coral_BranchB": build_branch_coral("Coral_BranchB", 0.42, branches=3, sub_branches=False),
    "Coral_Brain": build_brain_coral(),
    "Coral_TubeA": build_tube_cluster("Coral_TubeA", 7, (0.20, 0.34), (0.040, 0.055), 0.11),
    "Coral_TubeB": build_tube_cluster("Coral_TubeB", 6, (0.12, 0.22), (0.045, 0.065), 0.10),
    "Coral_Plate": build_plate_coral(),
    "Coral_Bush": build_bush_coral(),
}
for key, places in CORALS.items():
    for i, (x, y) in enumerate(places):
        s = rng.uniform(0.9, 1.1)
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
diver = new_empty("Diver", location=DIVER_LOCATION, rotation=tuple(math.radians(a) for a in DIVER_ROTATION_DEG))
new_object("Diver_Body", build_diver_body(), parent=diver)
new_object("Diver_Tank", build_diver_tank(), parent=diver)
new_object("Diver_Mask", build_diver_mask(), parent=diver)
fin_mesh = build_diver_fin()
new_object("Diver_Fin_L", fin_mesh, parent=diver, location=(-0.41, 0.10, 0.0))
new_object("Diver_Fin_R", fin_mesh, parent=diver, location=(-0.41, -0.10, 0.0))

# --------------------------------------------------------------------------
# Build: fish
# --------------------------------------------------------------------------
fish_root = new_empty("Fish_Root")
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
# Camera, lighting, render settings (graybox: workbench, flat grey)
# --------------------------------------------------------------------------
cam_data = bpy.data.cameras.new("Camera")
cam = new_object("Camera", cam_data)
scene.camera = cam

world = bpy.data.worlds.new("World")
scene.world = world
world.color = (0.16, 0.19, 0.24)

scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x, scene.render.resolution_y = RENDER_SIZE
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.display.render_aa = "8"
shading = scene.display.shading
shading.light = "STUDIO"
shading.color_type = "SINGLE"
shading.single_color = (0.62, 0.62, 0.62)
shading.show_cavity = True
shading.cavity_type = "BOTH"
shading.show_shadows = True
shading.show_object_outline = True
shading.background_type = "WORLD"
scene.view_settings.view_transform = "Standard"


def place_camera(azimuth_deg, elevation_deg, distance, lens):
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    target = Vector(RENDER_TARGET)
    cam.location = target + Vector((
        distance * math.cos(el) * math.sin(az),
        -distance * math.cos(el) * math.cos(az),
        distance * math.sin(el),
    ))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = lens


os.makedirs(RENDER_DIR, exist_ok=True)
for view_name, (az, el, dist, lens) in VIEWS.items():
    place_camera(az, el, dist, lens)
    scene.render.filepath = os.path.join(RENDER_DIR, f"{view_name}.png")
    bpy.ops.render.render(write_still=True)

# Leave the camera on the hero view in the saved .blend.
place_camera(*VIEWS["hero"])

# --------------------------------------------------------------------------
# Hierarchy report
# --------------------------------------------------------------------------
def tri_count(mesh):
    return sum(len(p.vertices) - 2 for p in mesh.polygons)


lines = []
total_tris = 0
unique_meshes = set()


def walk(obj, depth=0):
    global total_tris
    pad = "  " * depth
    if obj.type == "MESH":
        t = tri_count(obj.data)
        total_tris += t
        unique_meshes.add(obj.data.name)
        d = obj.dimensions
        lines.append(f"{pad}{obj.name}  [MESH {obj.data.name}]  tris={t}  dims=({d.x:.2f}, {d.y:.2f}, {d.z:.2f})")
    else:
        lines.append(f"{pad}{obj.name}  [{obj.type}]")
    for child in sorted(obj.children, key=lambda o: o.name):
        walk(child, depth + 1)


bpy.context.view_layer.update()
for root in sorted((o for o in scene.objects if o.parent is None), key=lambda o: o.name):
    walk(root)

unique_tris = sum(tri_count(bpy.data.meshes[n]) for n in unique_meshes)
mesh_objects = [o for o in scene.objects if o.type == "MESH"]
summary = [
    "",
    f"mesh objects: {len(mesh_objects)}",
    f"unique meshes: {len(unique_meshes)}",
    f"unique triangles: {unique_tris}",
    f"scene triangles (with instances): {total_tris}",
]
report = "\n".join(lines + summary)
with open(REPORT_PATH, "w", encoding="utf-8") as fh:
    fh.write(report + "\n")
print(report)

# --------------------------------------------------------------------------
# Save
# --------------------------------------------------------------------------
os.makedirs(os.path.dirname(BLEND_PATH), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
print(f"GRAYBOX_OK blender={bpy.app.version_string}")
print(f"  blend:   {BLEND_PATH}")
print(f"  renders: {RENDER_DIR}")
