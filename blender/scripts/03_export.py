"""Step 06: export the audited reef and verify it in a fresh Blender process.

blender --background --factory-startup --threads 2 --python-exit-code 1 --python blender/scripts/03_export.py
Then run the independent Khronos validator: npm --prefix tools/gltf run validate
The authored .blend is only read; cameras/lights are added solely to import renders.
"""
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'blender/scenes/02_detail.blend'
OUTPUT = ROOT / 'export'
GLB = OUTPUT / 'reef.glb'
EVIDENCE = ROOT / 'blender/renders/export'
FINAL = ROOT / 'blender/renders/final'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def asset_objects():
    root = bpy.data.objects['Scene_Root']
    return sorted([root, *root.children_recursive], key=lambda obj: obj.name)


def tri_count(mesh):
    return sum(len(p.vertices) - 2 for p in mesh.polygons)


def scene_snapshot():
    objects = asset_objects()
    records, points, groups = {}, [], {}
    for obj in objects:
        record = {'type': obj.type, 'parent': obj.parent.name if obj.parent else None,
                  'world_matrix': [list(row) for row in obj.matrix_world]}
        if obj.type == 'MESH':
            positions = [obj.matrix_world @ v.co for v in obj.data.vertices]
            points.extend(positions)
            record.update(triangles=tri_count(obj.data), points=positions,
                          materials=[m.name for m in obj.data.materials],
                          palette_uvs=sorted({tuple(round(float(c), 5) for c in loop.uv) for loop in obj.data.uv_layers.active.data}))
            groups.setdefault(obj.data.name, []).append(obj.name)
        records[obj.name] = record
    material = bpy.data.materials['Reef_Palette']
    bsdf = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    textures = [n.image for n in material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
    image = textures[0]
    pixels = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(pixels)
    return {'objects': records, 'mesh_groups': sorted(sorted(names) for names in groups.values()),
            'triangles': sum(r.get('triangles', 0) for r in records.values()),
            'bounds': {'min': [min(p[i] for p in points) for i in range(3)],
                       'max': [max(p[i] for p in points) for i in range(3)]},
            'material': {'name': material.name, 'roughness': bsdf.inputs['Roughness'].default_value,
                         'metallic': bsdf.inputs['Metallic'].default_value, 'image_size': list(image.size),
                         'image_count': len(textures), 'pixels_sha256': hashlib.sha256(np.rint(pixels * 255).astype(np.uint8).tobytes()).hexdigest()}}


def authored_view_parameters():
    # Read literal parameters without executing the model builder.
    wanted = {'VIEWS', 'RENDER_TARGET', 'DIVER_LOCATION'}
    result = {}
    for node in ast.parse((ROOT / 'blender/scripts/02_detail.py').read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in wanted:
                    result[target.id] = ast.literal_eval(node.value)
    assert result.keys() == wanted
    return result


def inspect_glb():
    data = GLB.read_bytes()
    magic, version, length = struct.unpack_from('<4sII', data)
    assert (magic, version, length) == (b'glTF', 2, len(data))
    chunk_size, chunk_type = struct.unpack_from('<I4s', data, 12)
    assert chunk_type == b'JSON'
    doc = json.loads(data[20:20 + chunk_size])
    nodes, meshes = doc['nodes'], doc['meshes']
    names = [node.get('name') for node in nodes]
    expected = {obj.name for obj in asset_objects()}
    assert len(names) == len(set(names)) and set(names) == expected, 'Interaction node names changed'
    assert not doc.get('animations') and not doc.get('cameras')
    assert 'KHR_lights_punctual' not in doc.get('extensionsUsed', [])
    assert 'EXT_mesh_gpu_instancing' not in doc.get('extensionsUsed', [])
    assert all('uri' not in b for b in doc.get('buffers', []))
    assert all('uri' not in image for image in doc.get('images', []))
    mesh_triangles = []
    for mesh in meshes:
        count = 0
        for primitive in mesh['primitives']:
            assert primitive.get('mode', 4) == 4
            assert {'POSITION', 'NORMAL', 'TEXCOORD_0'} <= primitive['attributes'].keys()
            assert primitive['material'] == 0
            count += doc['accessors'][primitive['indices']]['count'] // 3
        mesh_triangles.append(count)
    total = sum(mesh_triangles[node['mesh']] for node in nodes if 'mesh' in node)
    unique = sum(mesh_triangles)
    assert len(data) < 1_500_000, 'Project GLB size budget is 1.5 MB'
    assert total == 49420 and unique == 16690
    assert len(meshes) == 26 and sum('mesh' in n for n in nodes) == 91
    assert len(doc.get('materials', [])) == 1 and len(doc.get('textures', [])) == 1
    assert len(doc.get('images', [])) == 1
    pbr = doc['materials'][0]['pbrMetallicRoughness']
    assert abs(pbr['roughnessFactor'] - .55) < 1e-6 and pbr['metallicFactor'] == 0
    image_view = doc['bufferViews'][doc['images'][0]['bufferView']]
    binary_start = 20 + chunk_size + 8
    image_data = data[binary_start + image_view.get('byteOffset', 0):binary_start + image_view.get('byteOffset', 0) + image_view['byteLength']]
    assert image_data[:8] == b'\x89PNG\r\n\x1a\n'
    assert struct.unpack_from('>II', image_data, 16) == (64, 64)
    lines = []
    def walk(index, depth=0):
        node = nodes[index]
        info = f" mesh={node['mesh']} triangles={mesh_triangles[node['mesh']]}" if 'mesh' in node else ' [empty]'
        lines.append('  ' * depth + node['name'] + info)
        for child in node.get('children', []):
            walk(child, depth + 1)
    for index in doc['scenes'][doc.get('scene', 0)]['nodes']:
        walk(index)
    (OUTPUT / 'hierarchy.txt').write_text('\n'.join(lines) + '\n')
    return {'bytes': len(data), 'size_mb_decimal': len(data) / 1_000_000,
            'mesh_nodes': 91, 'nodes': len(nodes), 'meshes': len(meshes),
            'triangles': total, 'unique_triangles': unique, 'materials': 1, 'textures': 1,
            'texture_size': [64, 64], 'animations': 0, 'cameras': 0, 'lights': 0,
            'extensions_used': doc.get('extensionsUsed', []), 'draco': False,
            'up_axis': '+Y', 'embedded_resources_only': True,
            'mesh_triangles': mesh_triangles,
            'draw_calls_before_runtime_instancing': 91,
            'draw_call_note': 'Shared glTF meshes reduce stored geometry, not draw calls. Runtime batching is a later Web task.'}


def export_asset():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    audit = json.loads((FINAL / 'technical_checks.json').read_text())
    manifest = json.loads((FINAL / 'render_manifest.json').read_text())
    assert audit['pass'] and manifest['technical_checks_pass']
    assert sha(SOURCE) == manifest['artifact_sha256'], 'Rerun Step 05 after changing the source blend'
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    source_hash = sha(SOURCE)
    keep = set(asset_objects())
    excluded = []
    for obj in list(bpy.context.scene.objects):
        if obj not in keep or obj.hide_render or obj.hide_viewport or obj.hide_get():
            excluded.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    objects = asset_objects()
    assert len(objects) == 95
    for obj in objects:
        assert obj.type in ('EMPTY', 'MESH')
        assert all(math.isfinite(value) for row in obj.matrix_world for value in row)
        assert min(obj.scale) > 0 and max(obj.scale) - min(obj.scale) < 1e-5
        assert not obj.modifiers, 'Audited model should have no remaining modifiers'
        obj.select_set(True)
    for kind in ('meshes', 'materials', 'images'):
        blocks = getattr(bpy.data, kind)
        for block in list(blocks):
            if block.users == 0:
                blocks.remove(block)
    bpy.context.view_layer.objects.active = bpy.data.objects['Scene_Root']
    bpy.ops.export_scene.gltf(
        filepath=str(GLB), export_format='GLB', use_selection=True, use_visible=True,
        use_renderable=True, export_yup=True, export_apply=True,
        export_shared_accessors=True, export_texcoords=True, export_normals=True,
        export_tangents=False, export_materials='EXPORT', export_image_format='AUTO',
        export_vertex_color='NONE', export_attributes=False, export_extras=True,
        export_cameras=False, export_lights=False, export_animations=False,
        export_skins=False, export_morph=False, export_gpu_instances=False,
        export_draco_mesh_compression_enable=False,
    )
    stats = inspect_glb()
    write(OUTPUT / 'asset_manifest.json', {
        'asset': 'reef.glb', 'blender': bpy.app.version_string, 'source': str(SOURCE.relative_to(ROOT)),
        'source_sha256': source_hash, 'export_script_sha256': sha(Path(__file__)), 'glb_sha256': sha(GLB),
        'excluded_objects': excluded,
        'transform_policy': 'Retain audited positive uniform placement transforms and interaction pivots. Apply modifiers on export; none remain. Do not bake individual instances into unique meshes.',
        **stats,
    })
    assert sha(SOURCE) == source_hash, 'The authored blend must not be modified'
    command = [bpy.app.binary_path, '--background', '--factory-startup', '--threads', '2',
               '--python-exit-code', '1', '--python', str(Path(__file__).resolve()), '--', '--verify']
    subprocess.run(command, cwd=ROOT, check=True)
    print('EXPORT_OK', json.dumps(stats))


def maximum_point_distance(a, b):
    tree = KDTree(len(b))
    for index, point in enumerate(b):
        tree.insert(point, index)
    tree.balance()
    return max(tree.find(point)[2] for point in a)


def verify_import():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    before = scene_snapshot()
    source_scene = bpy.context.scene
    render_settings = {'engine': source_scene.render.engine, 'resolution_x': source_scene.render.resolution_x,
                       'resolution_y': source_scene.render.resolution_y, 'samples': source_scene.eevee.taa_render_samples,
                       'view_transform': source_scene.view_settings.view_transform, 'look': source_scene.view_settings.look,
                       'exposure': source_scene.view_settings.exposure, 'gamma': source_scene.view_settings.gamma}
    lighting_names = [o.name for o in source_scene.objects if o.type in ('CAMERA', 'LIGHT')]
    world_name = source_scene.world.name
    bpy.ops.wm.read_factory_settings(use_empty=True)
    assert len(bpy.data.objects) == 0
    bpy.ops.import_scene.gltf(filepath=str(GLB), import_shading='NORMALS', merge_vertices=False, import_pack_images=True)
    bpy.context.view_layer.update()
    after = scene_snapshot()
    errors, measurements = [], []
    if before['objects'].keys() != after['objects'].keys():
        errors.append('Node names changed')
    for name, original in before['objects'].items():
        current = after['objects'].get(name)
        if current is None:
            continue
        if original['parent'] != current['parent'] or original['type'] != current['type']:
            errors.append(f'Hierarchy/type changed: {name}')
        transform_delta = max(abs(a - b) for oldrow, newrow in zip(original['world_matrix'], current['world_matrix']) for a, b in zip(oldrow, newrow))
        if transform_delta > 1e-5:
            errors.append(f'Transform/pivot changed: {name}')
        row = {'object': name, 'matrix_max_error': transform_delta}
        if original['type'] == 'MESH':
            distance = max(maximum_point_distance(original['points'], current['points']),
                           maximum_point_distance(current['points'], original['points']))
            row['world_vertex_max_distance_m'] = distance
            if distance > 1e-5 or original['triangles'] != current['triangles']:
                errors.append(f'Geometry changed: {name}')
            if original['materials'] != current['materials'] or original['palette_uvs'] != current['palette_uvs']:
                errors.append(f'Material/UV changed: {name}')
        measurements.append(row)
    if before['mesh_groups'] != after['mesh_groups']:
        errors.append('Shared mesh assignments changed')
    if before['material'] != after['material']:
        errors.append('Material or palette pixels changed')
    if before['triangles'] != after['triangles']:
        errors.append('Scene triangle count changed')
    report = {'glb_sha256': sha(GLB), 'source_sha256': sha(SOURCE), 'fresh_process': True,
              'empty_scene_before_import': True, 'import_merge_vertices': False,
              'geometry_tolerance_m': 1e-5, 'measurements': measurements,
              'source_bounds_blender_z_up': before['bounds'], 'import_bounds_blender_z_up': after['bounds'],
              'triangles': after['triangles'], 'shared_mesh_groups_preserved': before['mesh_groups'] == after['mesh_groups'],
              'material': after['material'], 'errors': errors}
    write(OUTPUT / 'roundtrip_checks.json', report)
    assert not errors, errors

    # Add only the exact authored presentation; imported mesh data is untouched.
    with bpy.data.libraries.load(str(SOURCE), link=False) as (available, loaded):
        loaded.objects = lighting_names
        loaded.worlds = [world_name]
    scene = bpy.context.scene
    for obj in loaded.objects:
        scene.collection.objects.link(obj)
    scene.world = loaded.worlds[0]
    camera = next(o for o in loaded.objects if o.type == 'CAMERA')
    scene.camera = camera
    scene.render.engine = render_settings['engine']
    scene.render.resolution_x, scene.render.resolution_y = render_settings['resolution_x'], render_settings['resolution_y']
    scene.render.resolution_percentage = 100
    scene.render.threads_mode, scene.render.threads = 'FIXED', 2
    scene.eevee.taa_render_samples = render_settings['samples']
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    for key in ('view_transform', 'look', 'exposure', 'gamma'):
        setattr(scene.view_settings, key, render_settings[key])
    parameters = authored_view_parameters()
    views = {name: (*settings, parameters['RENDER_TARGET']) for name, settings in parameters['VIEWS'].items()}
    views.update({label: (az, el, 1.7, 60, parameters['DIVER_LOCATION']) for label, az, el in
                  [('diver_front', -20, 12), ('diver_back', 155, 20), ('diver_side', 75, 12)]})
    image_diffs = {}
    for name, (az, el, distance, lens, target) in views.items():
        az, el, target = math.radians(az), math.radians(el), Vector(target)
        camera.location = target + Vector((distance * math.cos(el) * math.sin(az), -distance * math.cos(el) * math.cos(az), distance * math.sin(el)))
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.lens = lens
        scene.render.filepath = str(EVIDENCE / f'{name}.png')
        bpy.ops.render.render(write_still=True)
        arrays = []
        for path in (FINAL / f'{name}.png', EVIDENCE / f'{name}.png'):
            image = bpy.data.images.load(str(path), check_existing=False)
            values = np.empty(len(image.pixels), dtype=np.float32)
            image.pixels.foreach_get(values)
            arrays.append(values.reshape(-1, 4)[:, :3])
            bpy.data.images.remove(image)
        delta = np.abs(arrays[0] - arrays[1])
        mae, fraction = float(delta.mean()), float(np.mean(delta.max(axis=1) > .05))
        image_diffs[name] = {'mean_absolute_rgb_delta_0_to_1': mae, 'fraction_pixels_delta_over_0_05': fraction,
                             'source_sha256': sha(FINAL / f'{name}.png'), 'import_sha256': sha(EVIDENCE / f'{name}.png')}
        if mae > .005 or fraction > .02:
            errors.append(f'Render difference exceeds gate: {name}')

    def sheet(destination, frames, columns, width=512, height=384):
        rows = math.ceil(len(frames) / columns)
        pixels = np.zeros((height * rows, width * columns, 4), dtype=np.float32)
        for index, path in enumerate(frames):
            image = bpy.data.images.load(str(path), check_existing=False)
            image.scale(width, height)
            values = np.empty(width * height * 4, dtype=np.float32)
            image.pixels.foreach_get(values)
            row, col = rows - 1 - index // columns, index % columns
            pixels[row * height:(row + 1) * height, col * width:(col + 1) * width] = values.reshape(height, width, 4)
            bpy.data.images.remove(image)
        image = bpy.data.images.new('Comparison', width=width * columns, height=height * rows, alpha=True)
        image.pixels.foreach_set(pixels.ravel())
        image.filepath_raw, image.file_format = str(destination), 'PNG'
        image.save()
        bpy.data.images.remove(image)
    sheet(EVIDENCE / 'contact_sheet.png', [EVIDENCE / f'{name}.png' for name in parameters['VIEWS']], 3)
    sheet(EVIDENCE / 'hero_comparison.png', [FINAL / 'hero.png', EVIDENCE / 'hero.png'], 2, 1024, 768)
    report.update(render_settings=render_settings, render_comparisons=image_diffs,
                  render_difference_gates={'mean_absolute_rgb_delta_max': .005, 'fraction_pixels_delta_over_0_05_max': .02},
                  errors=errors, passed=not errors)
    write(OUTPUT / 'roundtrip_checks.json', report)
    print('ROUNDTRIP_OK', json.dumps({'errors': errors, 'render_diffs': image_diffs}))
    assert not errors, errors


if __name__ == '__main__':
    if '--verify' in sys.argv:
        verify_import()
    else:
        export_asset()
