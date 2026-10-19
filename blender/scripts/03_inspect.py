"""Step 05 read-only audit of the saved model and its preserved Step 04 baseline.

blender --background --threads 2 --python-exit-code 1 --python blender/scripts/03_inspect.py
Writes technical_checks.json, scene_comparison.json and render_manifest.json.
Images still require human/agent visual review; this audit makes no aesthetic claim.
"""
import hashlib
import itertools
import json
import struct
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'blender/renders/final'
BASELINE = ROOT / 'blender/revisions/detail_before_step05/scenes/02_detail.blend'
ASSET = ROOT / 'blender/scenes/02_detail.blend'


def write(name, value):
    (OUTPUT / name).write_text(json.dumps(value, indent=2) + '\n')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def snapshot():
    result, points = {}, []
    for obj in sorted(bpy.context.scene.objects, key=lambda o: o.name):
        record = {'parent': obj.parent.name if obj.parent else None,
                  'matrix': [list(row) for row in obj.matrix_world], 'type': obj.type}
        if obj.type == 'MESH':
            mesh = obj.data
            record['geometry_uv_hash'] = digest([
                [list(v.co) for v in mesh.vertices],
                [list(p.vertices) for p in mesh.polygons],
                [[list(loop.uv) for loop in layer.data] for layer in mesh.uv_layers],
                [p.use_smooth for p in mesh.polygons]])
            record['mesh'] = mesh.name
            record['position_hash'] = digest([list(v.co) for v in mesh.vertices])
            record['materials'] = [m.name for m in mesh.materials]
            points.extend(obj.matrix_world @ Vector(p) for p in obj.bound_box)
        result[obj.name] = record
    bounds = {'min': [min(p[i] for p in points) for i in range(3)],
              'max': [max(p[i] for p in points) for i in range(3)]}
    return {'objects': result, 'bounds': bounds}


def components(bm):
    remaining = set(bm.verts)
    while remaining:
        stack, connected = [remaining.pop()], []
        while stack:
            vertex = stack.pop()
            connected.append(vertex)
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other in remaining:
                    remaining.remove(other)
                    stack.append(other)
        yield connected


def object_tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices],
                               [list(p.vertices) for p in obj.data.polygons])


def contact_report():
    objects = list(bpy.context.scene.objects)
    terrain = [o for o in objects if o.name == 'Sand' or o.name.startswith('Rock_')]
    trees = [(o, object_tree(o)) for o in terrain]

    def ground(x, y):
        heights = []
        for _obj, tree in trees:
            p, _n, _i, _d = tree.ray_cast(Vector((x, y, 7)), Vector((0, 0, -1)))
            if p is not None:
                heights.append(p.z)
        return max(heights) if heights else None

    contacts = []
    decorations = sorted([o for o in objects if o.name.startswith(('Coral_', 'Kelp_'))], key=lambda o: o.name)
    for obj in decorations:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for index, part in enumerate(components(bm)):
            lo, hi = min(v.co.z for v in part), max(v.co.z for v in part)
            # Fused organic bases are not perfectly planar; sample the lowest
            # 2 mm band, not only the single lowest vertex of a rounded root.
            roots = [obj.matrix_world @ v.co for v in part if v.co.z < lo + .002]
            gaps = [p.z - ground(p.x, p.y) for p in roots if ground(p.x, p.y) is not None]
            item = {'object': obj.name, 'component': index,
                    'minimum_root_gap_m': min(gaps) if gaps else None,
                    'maximum_root_gap_m': max(gaps) if gaps else None}
            if obj.name.startswith('Coral_Tube'):
                lips = [obj.matrix_world @ v.co for v in part if v.co.z > hi - .0001]
                item['minimum_lip_clearance_m'] = min(p.z - ground(p.x, p.y) for p in lips)
            contacts.append(item)
        bm.free()
    trees = {o.name: object_tree(o) for o in decorations}
    intersections = []
    for a, b in itertools.combinations(decorations, 2):
        pairs = trees[a.name].overlap(trees[b.name])
        if pairs:
            intersections.append({'objects': [a.name, b.name], 'triangle_pairs': len(pairs)})
    return {'method': 'Actual component base vertices raycast vertically onto final terrain; minimum gap <= 1mm indicates sampled base contact. Lip vertices must clear terrain by 45mm. Decoration BVH surface overlap checked separately. Not a global self-intersection proof.',
            'components': contacts, 'decoration_surface_intersections': intersections,
            'unsupported_components': [c for c in contacts if c['minimum_root_gap_m'] is None or c['minimum_root_gap_m'] > .001],
            'buried_tube_openings': [c for c in contacts if c.get('minimum_lip_clearance_m', 1) < .045 - 1e-5]}


if not BASELINE.exists():
    raise FileNotFoundError('Preserved Step 04 baseline is required for the regression comparison')
bpy.ops.wm.open_mainfile(filepath=str(BASELINE))
before = snapshot()
baseline_contacts = contact_report()
bpy.ops.wm.open_mainfile(filepath=str(ASSET))
after = snapshot()
scene = bpy.context.scene
errors, observations = [], {}
meshes = {o.data for o in scene.objects if o.type == 'MESH'}
mesh_results = []
for mesh in sorted(meshes, key=lambda m: m.name):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.normal_update()
    boundary = sum(e.is_boundary for e in bm.edges)
    inconsistent = sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
    inward = 0
    for part in components(bm):
        faces = {face for v in part for face in v.link_faces}
        edges = {edge for v in part for edge in v.link_edges}
        if edges and all(e.is_manifold for e in edges):
            volume = 0.0
            for face in faces:
                v = [p.co for p in face.verts]
                volume += sum(v[0].dot(v[i].cross(v[i + 1])) / 6 for i in range(1, len(v) - 1))
            inward += volume < -1e-12
    degenerate = sum(f.calc_area() < 1e-12 for f in bm.faces)
    unexpected_open = boundary if mesh.name != 'Sand' else 0
    bad_sand_normals = mesh.name == 'Sand' and any(f.normal.z <= 0 for f in bm.faces)
    triangles = sum(len(p.vertices) - 2 for p in mesh.polygons)
    row = {'mesh': mesh.name, 'triangles': triangles, 'boundary_edges': boundary,
           'inconsistent_winding_edges': inconsistent, 'inward_closed_components': inward,
           'degenerate_faces': degenerate}
    mesh_results.append(row)
    if inconsistent or inward or degenerate or unexpected_open or bad_sand_normals:
        errors.append({'topology_or_normals': row})
    if triangles > 20000:
        errors.append({'mesh_over_20k': mesh.name})
    if len(mesh.uv_layers) != 1 or len(mesh.materials) != 1:
        errors.append({'missing_palette_setup': mesh.name})
    bm.free()

transforms, origins = [], []
for obj in sorted(scene.objects, key=lambda o: o.name):
    if obj.type != 'MESH' and obj.name != 'Diver':
        continue
    if any(abs(v) > 1e-6 for v in obj.rotation_euler) or any(abs(v - 1) > 1e-6 for v in obj.scale):
        transforms.append({'object': obj.name, 'rotation_rad': list(obj.rotation_euler), 'scale': list(obj.scale)})
    if min(obj.scale) <= 0 or max(obj.scale) - min(obj.scale) > 1e-5:
        errors.append({'unexpected_scale': obj.name})
    if obj.modifiers:
        errors.append({'unapplied_modifiers': obj.name})
    if obj.type == 'MESH':
        corners = [Vector(p) for p in obj.bound_box]
        center = sum(corners, Vector()) / 8
        diagonal = (Vector([max(p[i] for p in corners) for i in range(3)]) - Vector([min(p[i] for p in corners) for i in range(3)])).length
        far = center.length > diagonal * 1.25
        if far:
            origins.append({'object': obj.name, 'local_center_distance_m': center.length,
                            'intentional': obj.name.startswith('Diver_'),
                            'reason': 'Diver accessories share the chest coordinate frame.'})
            if not obj.name.startswith('Diver_'):
                errors.append({'unexpected_origin_offset': obj.name})
observations['unapplied_placement_transforms'] = transforms
observations['transform_policy'] = 'Positive uniform placement scales and rotations are intentional for shared instances and the Diver root; no remaining modifiers.'
observations['origins_far_from_geometry_center'] = origins
observations['origin_policy'] = 'Rocks use base pivots; corals/kelp use root pivots; Diver accessories use the assembly coordinate frame. These intentionally differ from geometry centers.'

materials = [m for m in bpy.data.materials if m.users]
for material in materials:
    output = next((n for n in material.node_tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output), None) if material.use_nodes else None
    if output is None or not output.inputs['Surface'].links or output.inputs['Surface'].links[0].from_node.type != 'BSDF_PRINCIPLED':
        errors.append({'non_principled_material': material.name})
unused = {kind: [d.name for d in getattr(bpy.data, kind) if d.users == 0 and getattr(d, 'type', '') not in ('RENDER_RESULT', 'COMPOSITING')]
          for kind in ('meshes', 'materials', 'images')}
if any(unused.values()):
    errors.append({'unused_data': unused})
contacts = contact_report()
if contacts['unsupported_components'] or contacts['buried_tube_openings'] or contacts['decoration_surface_intersections']:
    errors.append({'contact_findings': {k: v for k, v in contacts.items() if k in ('unsupported_components', 'buried_tube_openings', 'decoration_surface_intersections')}})

old, new = before['objects'], after['objects']
comparison = {
    'names_preserved': old.keys() == new.keys(),
    'parenting_preserved': all(n in new and o['parent'] == new[n]['parent'] for n, o in old.items()),
    'non_sand_geometry_and_uvs_preserved': all(n in new and o.get('geometry_uv_hash') == new[n].get('geometry_uv_hash') for n, o in old.items() if n != 'Sand'),
    'sand_vertex_positions_preserved': old['Sand']['position_hash'] == new['Sand']['position_hash'],
    'sand_winding_repair': 'Open seabed explicitly faces upward; position and triangle count remain unchanged.',
    'shared_mesh_assignments_preserved': all(n in new and o.get('mesh') == new[n].get('mesh') for n, o in old.items()),
    'material_assignments_preserved': all(n in new and o.get('materials') == new[n].get('materials') for n, o in old.items()),
    'non_decoration_transforms_preserved': all(n in new and o['matrix'] == new[n]['matrix'] for n, o in old.items() if not n.startswith(('Coral_', 'Kelp_'))),
    'aggregate_bounds_within_1cm_preserved': max(abs(before['bounds'][side][i] - after['bounds'][side][i]) for side in ('min', 'max') for i in range(3)) < .01,
    'bounds_tolerance_reason': 'Allow shallow root embedding below the uneven seabed; X/Y extent and top height are unchanged.',
    'before_bounds': before['bounds'], 'after_bounds': after['bounds'],
    'changed_placements': [n for n in old if n in new and old[n]['matrix'] != new[n]['matrix']],
    'baseline_contact_summary': {k: v for k, v in baseline_contacts.items() if k not in ('components', 'method')},
}
if not all(value for key, value in comparison.items() if key.endswith('_preserved')):
    errors.append({'regression': comparison})
peak = bpy.data.objects['Rock_Peak_001']
maximum = max(v.co.z for v in peak.data.vertices)
coral_top = max((o.matrix_world @ v.co).z for o in scene.objects if o.name.startswith('Coral_') for v in o.data.vertices)
if abs(maximum - 1.65) > 1e-5 or sum(abs(v.co.z - maximum) < 1e-6 for v in peak.data.vertices) != 1 or coral_top > maximum - .15:
    errors.append({'single_peak_or_clearance': [maximum, coral_top]})
unique_triangles = sum(row['triangles'] for row in mesh_results)
triangles = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in scene.objects if o.type == 'MESH')
if triangles >= 100000 or unique_triangles >= 40000:
    errors.append({'budget': [triangles, unique_triangles]})
palette = bpy.data.images.get('Reef_Palette_64')
if len(materials) != 1 or palette is None or not palette.packed_file or list(palette.size) != [64, 64]:
    errors.append('Single packed 64x64 palette requirement failed')
render_files = {}
for label in ('hero', 'front', 'left', 'right', 'back', 'top', 'diver_front', 'diver_back', 'diver_side'):
    path = OUTPUT / f'{label}.png'
    if not path.exists():
        errors.append({'missing_render': path.name})
        continue
    data = path.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', data[16:24]) != (1024, 768):
        errors.append({'unexpected_render_format': path.name})
    render_files[path.name] = hashlib.sha256(data).hexdigest()
if json.loads((OUTPUT / 'build_report.json').read_text())['preview_only']:
    errors.append('Run a full build, not --preview, before the final audit')

write('scene_comparison.json', comparison)
write('technical_checks.json', {
    'asset': str(ASSET.relative_to(ROOT)), 'blender': bpy.app.version_string,
    'pass': not errors, 'errors': errors, 'triangles': triangles, 'unique_triangles': unique_triangles,
    'mesh_checks': mesh_results, 'observations': observations, 'unused_data': unused,
    'contacts': contacts, 'single_peak_height_m': maximum, 'highest_coral_m': coral_top,
})
bsdf = next(n for n in materials[0].node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
write('render_manifest.json', {
    'stage': 'Step 05', 'blender': bpy.app.version_string, 'engine': scene.render.engine,
    'resolution': [scene.render.resolution_x, scene.render.resolution_y],
    'render_samples': scene.eevee.taa_render_samples,
    'color_management': [scene.view_settings.view_transform, scene.view_settings.look],
    'packed_palette': bool(palette.packed_file), 'palette_pixels': list(palette.size),
    'material_count': len(materials), 'roughness': bsdf.inputs['Roughness'].default_value,
    'metallic': bsdf.inputs['Metallic'].default_value,
    'peak_height_m': maximum, 'highest_coral_m': coral_top, 'summit_clearance_m': maximum - coral_top,
    'render_views': ['hero', 'front', 'left', 'right', 'back', 'top'],
    'character_views': ['diver_front', 'diver_back', 'diver_side'],
    'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                      [ROOT / 'blender/scripts' / name for name in ('02_detail.py', 'detail_geometry.py', '03_inspect.py')]},
    'artifact_sha256': hashlib.sha256(ASSET.read_bytes()).hexdigest(),
    'render_sha256': render_files,
    'technical_checks_pass': not errors,
})
print('STEP05_AUDIT', json.dumps({'pass': not errors, 'errors': errors, 'triangles': triangles,
                                 'contact_components': len(contacts['components']),
                                 'unsupported_components': len(contacts['unsupported_components'])}))
if errors:
    raise RuntimeError('Step 05 technical checks failed; see technical_checks.json')
