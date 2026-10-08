"""Step 00 smoke test: empty scene -> cube -> 512x512 render -> save .blend.

Run headless:
    blender --background --python blender/scripts/smoke-test.py

Outputs (relative to repo root):
    blender/renders/smoke-test.png
    blender/scenes/smoke-test.blend
"""

import math
import os

import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RENDER_PATH = os.path.join(ROOT, "blender", "renders", "smoke-test.png")
BLEND_PATH = os.path.join(ROOT, "blender", "scenes", "smoke-test.blend")

# 1. Start from a truly empty scene (no default cube / camera / light).
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# 2. Add a cube.
bpy.ops.mesh.primitive_cube_add(size=2, location=(0.0, 0.0, 1.0))
cube = bpy.context.active_object
cube.name = "SmokeCube"

# Camera
cam_data = bpy.data.cameras.new("Camera")
cam = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(cam)
cam.location = (6.0, -6.0, 4.5)
cam.rotation_euler = (math.radians(60.0), 0.0, math.radians(45.0))
scene.camera = cam

# Light
sun_data = bpy.data.lights.new("Sun", "SUN")
sun_data.energy = 3.0
sun = bpy.data.objects.new("Sun", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50.0), 0.0, math.radians(30.0))

# 3. Render a single 512x512 frame with Eevee (fast); fall back if engine id differs.
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
    try:
        scene.render.engine = engine
        break
    except TypeError:
        continue

os.makedirs(os.path.dirname(RENDER_PATH), exist_ok=True)
scene.render.filepath = RENDER_PATH
bpy.ops.render.render(write_still=True)

# 4. Save the .blend.
os.makedirs(os.path.dirname(BLEND_PATH), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

print(f"SMOKE_TEST_OK blender={bpy.app.version_string} engine={scene.render.engine}")
print(f"  render: {RENDER_PATH}")
print(f"  blend:  {BLEND_PATH}")
