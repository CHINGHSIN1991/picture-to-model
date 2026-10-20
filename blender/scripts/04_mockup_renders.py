"""Step 09 - transparent per-section renders used by the website mockups.

Reads blender/scenes/02_detail.blend only (never saved back) and writes one PNG per
section to blender/renders/mockup/, each showing the groups that are at rest (t = 0)
at the END of that section, viewed from the model rotation the section specifies.

Camera convention: the mockup "model rotation" is a Y-up (Three.js) rotation of the
model; rotating the model by +r about its up axis equals orbiting the camera by -r,
so azimuth = HERO_AZIMUTH - rotation_deg. HERO_* values match VIEWS['hero'] in
02_detail.py so section 1 reproduces the Step 05/07 hero framing.

Usage:
  blender --background --factory-startup --threads 2 --python-exit-code 1 \
      --python blender/scripts/04_mockup_renders.py
"""
import json
import math
import os
import re

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BLEND_PATH = os.path.join(ROOT, 'blender', 'scenes', '02_detail.blend')
OUT_DIR = os.path.join(ROOT, 'blender', 'renders', 'mockup')
RENDER_SIZE = (1600, 1200)
RENDER_SAMPLES = 32
HERO_AZIMUTH, HERO_ELEVATION, HERO_DISTANCE, HERO_LENS = -12.0, 17.0, 6.8, 50.0
HERO_TARGET = (0.0, 0.0, 0.80)

# PROJECT_SPEC part groups -> Blender object-name patterns (Diver empty + children).
GROUPS = {
    'rocks': re.compile(r'^Rock_(Peak|Tier)_'),
    'boulders': re.compile(r'^Rock_Boulder_'),
    'corals': re.compile(r'^Coral_'),
    'kelp': re.compile(r'^Kelp_'),
    'fish': re.compile(r'^Fish_'),
    'diver': re.compile(r'^Diver'),
}
ALL = set(GROUPS)

# name, model rotation Y (deg, cumulative), elevation, distance factor, lens, target z, groups at rest
SECTIONS = [
    ('s1_hero',   0.0,   17.0, 1.00, 50.0, 0.80, ALL),
    ('s2_rocks',  -35.0, 21.0, 0.95, 50.0, 0.70, {'rocks', 'boulders'}),
    ('s3_life',   -100.0, 13.0, 0.80, 50.0, 0.70, {'rocks', 'boulders', 'corals', 'kelp'}),
    ('s4_diver',  -160.0, 9.0, 0.92, 50.0, 1.05, {'rocks', 'boulders', 'corals', 'kelp', 'diver'}),
    ('s5_fish',   -230.0, 26.0, 1.10, 50.0, 0.80, ALL),
    ('s6_cta',    -360.0, 30.0, 1.15, 50.0, 0.70, ALL),
]

bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)
scene = bpy.context.scene
cam = scene.camera
assert cam is not None, 'authored scene has no camera'
scene.render.film_transparent = True
scene.render.resolution_x, scene.render.resolution_y = RENDER_SIZE
scene.render.resolution_percentage = 100
scene.render.threads_mode, scene.render.threads = 'FIXED', 2
scene.eevee.taa_render_samples = RENDER_SAMPLES
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'

meshes = [o for o in scene.objects if o.type == 'MESH']


def group_of(name):
    for group, pattern in GROUPS.items():
        if pattern.match(name):
            return group
    return None  # Sand and anything unmatched always renders


def place_camera(azimuth_deg, elevation_deg, distance, lens, target):
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    target = Vector(target)
    cam.location = target + Vector((distance * math.cos(el) * math.sin(az),
                                    -distance * math.cos(el) * math.cos(az),
                                    distance * math.sin(el)))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens


os.makedirs(OUT_DIR, exist_ok=True)
manifest = {'blend': os.path.relpath(BLEND_PATH, ROOT), 'resolution': list(RENDER_SIZE),
            'samples': RENDER_SAMPLES, 'film_transparent': True, 'sections': []}
for name, rotation, elevation, factor, lens, target_z, visible in SECTIONS:
    hidden = 0
    for obj in meshes:
        group = group_of(obj.name)
        obj.hide_render = group is not None and group not in visible
        hidden += obj.hide_render
    azimuth = HERO_AZIMUTH - rotation
    place_camera(azimuth, elevation, HERO_DISTANCE * factor, lens, (0.0, 0.0, target_z))
    scene.render.filepath = os.path.join(OUT_DIR, f'{name}.png')
    bpy.ops.render.render(write_still=True)
    manifest['sections'].append({
        'file': f'{name}.png', 'rotation_y_deg': rotation, 'azimuth_deg': azimuth,
        'elevation_deg': elevation, 'distance': round(HERO_DISTANCE * factor, 3), 'lens_mm': lens,
        'target': [0.0, 0.0, target_z], 'groups_at_rest': sorted(visible),
        'groups_departed': sorted(ALL - visible), 'hidden_meshes': hidden,
    })
    print(f'MOCKUP_RENDER {name} rotation={rotation} azimuth={azimuth} hidden={hidden}')

for obj in meshes:
    obj.hide_render = False
with open(os.path.join(OUT_DIR, 'manifest.json'), 'w') as handle:
    json.dump(manifest, handle, indent=2)
print('MOCKUP_RENDERS_OK')
