"""Low-poly reef prototypes and a single exportable palette material.

Used by 02_detail.py. All random streams are local and deterministic.
"""
import math
import random
import struct
import zlib
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


SWATCHES = [
    ('rock', '3A5BA0'), ('rock_dark', '2E4A86'), ('rock_light', '6389BE'),
    ('sand', 'E8D9A8'), ('sand_light', 'F5E8C6'),
    ('red', 'E8546B'), ('pink', 'F27BA3'), ('pink_light', 'FFAEC8'),
    ('orange', 'F28C3B'), ('orange_light', 'FFD08A'),
    ('purple', '7A5BD6'), ('purple_dark', '423674'), ('blue', '4A6CF0'),
    ('yellow', 'F2C94C'), ('green', '3FA65B'), ('lime', 'B8C83A'),
    ('suit', '1F2E5C'), ('suit_light', '344A7E'), ('fin', '3A7BF0'),
    ('black', '142135'), ('white', 'F5F5F5'), ('skin', 'DCA78B'),
    ('lens', '4FCBD8'), ('lens_dark', '17546E'), ('fish_orange', 'F27B3B'),
]
C = {name: i for i, (name, _) in enumerate(SWATCHES)}


class Geo:
    def __init__(self):
        self.vertices, self.faces, self.colors = [], [], []

    def vertex(self, p):
        self.vertices.append(tuple(p))
        return len(self.vertices) - 1

    def face(self, indices, color):
        self.faces.append(tuple(indices))
        self.colors.append(C[color] if isinstance(color, str) else color)

    def loft(self, rings, color, caps=True):
        ids = [[self.vertex(p) for p in ring] for ring in rings]
        n = len(ids[0])
        if caps:
            self.face(reversed(ids[0]), color)
        for a, b in zip(ids, ids[1:]):
            for j in range(n):
                self.face((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]), color)
        if caps:
            self.face(ids[-1], color)
        return ids

    def tube(self, points, radii, color, sides=8):
        points = [Vector(p) for p in points]
        rings = []
        for i, (p, radius) in enumerate(zip(points, radii)):
            tangent = points[min(i + 1, len(points) - 1)] - points[max(0, i - 1)]
            tangent.normalize()
            axis = Vector((0, 1, 0)) if abs(tangent.y) < 0.85 else Vector((1, 0, 0))
            u = tangent.cross(axis).normalized()
            v = tangent.cross(u).normalized()
            rings.append([p + radius * (math.cos(j * math.tau / sides) * u + math.sin(j * math.tau / sides) * v) for j in range(sides)])
        return self.loft(rings, color)

    def ellipsoid(self, center, scale, color, segments=12, levels=7):
        center, scale = Vector(center), Vector(scale)
        rings = []
        for k in range(1, levels):
            phi = math.pi * k / levels
            rings.append([center + Vector((scale.x * math.sin(phi) * math.cos(math.tau * j / segments),
                                           scale.y * math.sin(phi) * math.sin(math.tau * j / segments),
                                           scale.z * math.cos(phi))) for j in range(segments)])
        ids = self.loft(rings, color, caps=False)
        north = self.vertex(center + Vector((0, 0, scale.z)))
        south = self.vertex(center - Vector((0, 0, scale.z)))
        for j in range(segments):
            self.face((north, ids[0][j], ids[0][(j + 1) % segments]), color)
            self.face((south, ids[-1][(j + 1) % segments], ids[-1][j]), color)

    def mesh(self, name, smooth=True):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertices, [], self.faces)
        for polygon, color in zip(mesh.polygons, self.colors):
            polygon.material_index = color
            polygon.use_smooth = smooth
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        return mesh


def fuse(mesh, voxel, triangles, color):
    """Union continuous organic surfaces, then bound evaluated topology cost."""
    obj = bpy.data.objects.new('_Prototype', mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    mod = obj.modifiers.new('OrganicUnion', 'REMESH')
    mod.mode = 'VOXEL'
    mod.voxel_size = voxel
    mod.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mod = obj.modifiers.new('JointRelax', 'SMOOTH')
    mod.factor = 0.65
    mod.iterations = 3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    count = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    mod = obj.modifiers.new('WebBudget', 'DECIMATE')
    mod.ratio = min(1.0, triangles / max(count, 1))
    bpy.ops.object.modifier_apply(modifier=mod.name)
    result = obj.data
    result.name = mesh.name + '_Union'
    for p in result.polygons:
        p.material_index = C[color]
        p.use_smooth = True
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh != result and mesh.users == 0:
        bpy.data.meshes.remove(mesh)
    return result


def build_branch_coral(name, height, branches, sub_branches=True):
    r = random.Random(201 if sub_branches else 202)
    g = Geo()
    h = height
    color = 'red' if sub_branches else 'pink'
    g.tube([(0, 0, -0.015), (0, 0, h * 0.18), (h * 0.025, 0, h * 0.43)],
           [h * 0.09, h * 0.075, h * 0.045], color)
    for i in range(branches):
        angle = math.tau * i / branches + r.uniform(-0.18, 0.18)
        direction = Vector((math.cos(angle), math.sin(angle), 0))
        start = Vector((0, 0, h * (0.18 + i % 2 * 0.06)))
        points = [start + direction * h * t * 0.45 + Vector((0, 0, h * (0.50 * t + 0.08 * t * t))) for t in (0, .25, .5, .75, 1)]
        g.tube(points, [h * v for v in (.068, .059, .048, .036, .020)], color)
        g.ellipsoid(points[-1], (h * .023,) * 3, color, 8, 4)
        if sub_branches:
            for j, sign in enumerate((-1, 1)):
                fork_angle = angle + sign * .62
                d = Vector((math.cos(fork_angle), math.sin(fork_angle), 0))
                p = points[2 + j]
                tips = [p + d * h * .24 * t + Vector((0, 0, h * .24 * t)) for t in (0, .4, .75, 1)]
                g.tube(tips, [h * v for v in (.039, .030, .022, .014)], color, 7)
                g.ellipsoid(tips[-1], (h * .017,) * 3, color, 7, 4)
    mesh = fuse(g.mesh(name), h * .014, 2400 if sub_branches else 900, color)
    # Pink terminal surfaces are baked into the common atlas UVs below.
    for p in mesh.polygons:
        z = sum(mesh.vertices[v].co.z for v in p.vertices) / len(p.vertices)
        if z > h * .75:
            p.material_index = C['pink_light' if not sub_branches else 'pink']
    return mesh


def build_brain_coral():
    g = Geo()
    g.ellipsoid((0, 0, .145), (.205, .185, .145), 'pink', 24, 14)
    mesh = g.mesh('Coral_Brain', smooth=False)
    for v in mesh.vertices:
        p = v.co
        wobble = 1 + .025 * math.sin(p.x * 63) * math.cos(p.y * 57)
        p.x *= wobble
        p.y *= wobble
        p.z = max(0.0, p.z)
    # The brief excludes modeled brain grooves; subtle facet colors give relief.
    for p in mesh.polygons:
        center = sum((mesh.vertices[v].co for v in p.vertices), Vector()) / len(p.vertices)
        p.material_index = C['pink_light' if center.z > .22 and math.sin(center.x * 18 + center.y * 12) > .55 else 'pink']
    # Remove any flattened underside faces with zero area.
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh); bm.free()
    return mesh


def build_tube_cluster(name, count, height_range, radius_range, spread):
    r = random.Random(301 if name.endswith('A') else 302)
    g = Geo()
    for i in range(count):
        angle = math.tau * i / count
        d = spread * (.35 if i == 0 else r.uniform(.65, 1))
        base = Vector((math.cos(angle) * d, math.sin(angle) * d, -.012))
        h, radius = r.uniform(*height_range), r.uniform(*radius_range)
        lean = Vector((math.cos(angle) * h * .12, math.sin(angle) * h * .12, 0))
        color = ('orange', 'pink', 'red')[i % 3] if name.endswith('A') else ('purple', 'blue')[i % 2]
        light = 'orange_light' if name.endswith('A') else 'pink'
        rings = []
        # Outer wall, rounded lip, inner wall, closed inner floor.
        for t, rad in ((0, .72), (.40, .88), (.88, 1.0), (1, .95), (1, .66), (.88, .64), (.35, .48)):
            rings.append([base + lean * t + Vector((math.cos(a * math.tau / 10) * radius * rad,
                                                   math.sin(a * math.tau / 10) * radius * rad, h * t)) for a in range(10)])
        ids = g.loft(rings, color, caps=False)
        g.face(reversed(ids[0]), color)
        g.face(ids[-1], 'purple_dark' if name.endswith('B') else 'red')
        # The fourth strip is the visible ring around the hollow opening.
        start = len(g.colors) - 2 - 6 * 10
        for j in range(start + 3 * 10, start + 4 * 10):
            g.colors[j] = C[light]
        for j in range(start + 4 * 10, start + 6 * 10):
            g.colors[j] = C['purple_dark' if name.endswith('B') else 'red']
    return g.mesh(name)


def build_plate_coral():
    g = Geo()
    rings = []
    profile = [(0, .026), (.045, .032), (.075, .09), (.12, .20), (.15, .235), (.165, .23), (.14, .19), (.095, .065)]
    for k, (height, radius) in enumerate(profile):
        ring = []
        for j in range(32):
            a = j * math.tau / 32
            wave = math.sin(a * 7 + .4) * .014 * (radius / .235) ** 2
            rr = radius * (1 + .055 * math.sin(a * 5))
            ring.append((math.cos(a) * rr, math.sin(a) * rr, height + wave))
        rings.append(ring)
    ids = g.loft(rings, 'orange', caps=False)
    g.face(reversed(ids[0]), 'orange')
    g.face(ids[-1], 'orange_light')
    for i in range(4 * 32, 7 * 32):
        g.colors[i] = C['orange_light' if i < 5 * 32 else 'orange']
    return g.mesh('Coral_Plate')


def build_bush_coral():
    g = Geo()
    r = random.Random(401)
    for i in range(9):
        a = math.tau * i / 9
        h = r.uniform(.12, .22)
        d = Vector((math.cos(a), math.sin(a), 0))
        root = d * .035
        points = [root + d * .065 * t + Vector((0, 0, h * t)) for t in (0, .4, .8, 1)]
        g.tube(points, [.026, .025, .020, .012], 'yellow', 7)
        g.ellipsoid(points[-1], (.014, .014, .018), 'yellow', 7, 4)
    return fuse(g.mesh('Coral_Bush'), .007, 900, 'yellow')


def build_kelp(name, height, lean_deg):
    g = Geo()
    color = 'green' if name.endswith('A') else 'lime'
    for blade in range(3):
        h = height * (1 - .12 * blade)
        rings = []
        for i in range(10):
            t = i / 9
            width = .007 + .024 * math.sin(math.pi * t) ** .7
            if i == 9:
                width = .0015
            x = (blade - 1) * .038 * t + math.sin(t * math.pi * 2.2 + blade * .4) * .035 * t
            y = math.sin(t * math.pi * 1.5) * math.radians(lean_deg) * .09
            z = h * t
            rings.append([(x - width, y - .004, z), (x + width, y - .004, z),
                          (x + width, y + .004, z), (x - width, y + .004, z)])
        g.loft(rings, color)
    return g.mesh(name)


def build_fish(name, length, body_ratio):
    g = Geo()
    color = {'Fish_A': 'yellow', 'Fish_B': 'fish_orange', 'Fish_C': 'blue'}[name]
    g.ellipsoid((0, 0, 0), (length * .40, length * .14, length * body_ratio), color, 10, 6)
    # Tangible triangular tail and dorsal fin, not coincident double faces.
    for points in [
        [(-.34, 0, 0), (-.61, 0, .21), (-.61, 0, -.21)],
        [(-.18, 0, .18), (.10, 0, .20), (-.08, 0, .36)],
    ]:
        rings = [[(x * length, y + side * length * .018, z * length) for x, y, z in points] for side in (-1, 1)]
        g.loft(rings, color)
    for side in (-1, 1):
        g.ellipsoid((length * .23, side * length * .125, length * .055), (length * .035,) * 3, 'black', 6, 3)
    mesh = g.mesh(name, smooth=False)
    if name == 'Fish_B':
        for p in mesh.polygons:
            if p.material_index != C[color]:
                continue
            x = sum(mesh.vertices[v].co.x for v in p.vertices) / len(p.vertices) / length
            if abs(x + .18) < .055 or abs(x - .13) < .055:
                p.material_index = C['white']
    return mesh


def build_diver_body():
    g = Geo()
    g.ellipsoid((0, 0, 0), (.145, .075, .052), 'suit', 16, 9)
    g.ellipsoid((-.12, 0, 0), (.073, .068, .052), 'suit', 12, 7)
    g.tube([(.10, 0, 0), (.16, 0, .007)], [.033, .030], 'suit')
    g.ellipsoid((.195, 0, .005), (.061, .055, .060), 'suit', 16, 9)
    for side in (-1, 1):
        g.tube([(.065, side * .055, 0), (.11, side * .12, -.012), (.18, side * .16, -.05), (.25, side * .16, -.06)],
               [.034, .029, .024, .020], 'suit', 10)
        g.ellipsoid((.265, side * .16, -.06), (.035, .020, .016), 'suit', 10, 5)
        g.ellipsoid((.253, side * .14, -.058), (.017, .011, .010), 'suit', 8, 4)
        g.tube([(-.13, side * .038, 0), (-.24, side * .055, -.035), (-.30, side * .065, -.05), (-.41, side * .10, 0)],
               [.041, .033, .028, .022], 'suit', 10)
        g.ellipsoid((-.30, side * .065, -.05), (.032, .029, .028), 'suit', 10, 5)
    mesh = fuse(g.mesh('Diver_Body'), .0045, 3200, 'suit')
    # Accessory surfaces remain fitted but independent of the fused wetsuit.
    extras = Geo()
    extras.ellipsoid((.195, 0, -.035), (.044, .044, .032), 'skin', 14, 7)
    surface = BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices], [list(p.vertices) for p in mesh.polygons])
    for side in (-1, 1):
        strap = []
        for x, y in ((.10, .040), (.055, .050), (0, .054), (-.045, .049), (-.09, .040)):
            hit, _normal, _index, _distance = surface.ray_cast(Vector((x, side * y, -.3)), Vector((0, 0, 1)))
            assert hit is not None, 'Chest strap must contact the wetsuit'
            strap.append((x, side * y, hit.z - .003))
        extras.tube(strap, [.006] * len(strap), 'black', 6)
    extras.ellipsoid((-.075, 0, -.052), (.015, .021, .008), 'yellow', 8, 4)
    addon = extras.mesh('Diver_HarnessAndFace')
    bm = bmesh.new(); bm.from_mesh(mesh); bm.from_mesh(addon)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh); bm.free(); bpy.data.meshes.remove(addon)
    return mesh


def build_diver_tank():
    g = Geo()
    g.ellipsoid((-.015, 0, .078), (.125, .043, .043), 'yellow', 14, 9)
    for x in (-.073, .045):
        points = [(x, math.cos(a * math.tau / 16) * .044, .078 + math.sin(a * math.tau / 16) * .044) for a in range(17)]
        g.tube(points, [.007] * len(points), 'black', 6)
    g.tube([(.10, 0, .078), (.13, 0, .078)], [.014, .012], 'black', 8)
    # Regulator hose follows the neck and reaches the mask's mouthpiece.
    a, b, c, d = map(Vector, ((.12, 0, .078), (.22, -.09, .09), (.22, -.09, -.075), (.15, 0, -.068)))
    hose = [(1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d for t in [i / 16 for i in range(17)]]
    g.tube(hose, [.006] * len(hose), 'black', 6)
    return g.mesh('Diver_Tank')


def build_diver_mask():
    g = Geo()
    for side in (-1, 1):
        g.ellipsoid((.208, side * .023, -.060), (.030, .027, .012), 'fin', 12, 5)
        g.ellipsoid((.208, side * .023, -.069), (.024, .021, .006), 'lens_dark', 12, 5)
        g.ellipsoid((.214, side * .023, -.074), (.012, .014, .002), 'lens', 8, 4)
    g.ellipsoid((.173, 0, -.067), (.018, .014, .016), 'skin', 10, 5)
    g.ellipsoid((.15, 0, -.068), (.019, .021, .014), 'black', 10, 5)
    return g.mesh('Diver_Mask')


def build_diver_fin():
    g = Geo()
    rings = []
    for x, width, z in ((.015, .020, 0), (-.04, .027, -.005), (-.12, .048, -.02), (-.18, .042, -.03)):
        rings.append([(x, -width, z - .004), (x, width, z - .004), (x, width, z + .004), (x, -width, z + .004)])
    g.loft(rings, 'fin')
    g.ellipsoid((-.018, 0, .008), (.040, .023, .017), 'suit', 10, 5)
    for side in (-1, 1):
        g.tube([(-.045, side * .021, .004), (-.12, side * .034, -.01), (-.172, side * .033, -.021)], [.0035] * 3, 'lens', 5)
    return g.mesh('Diver_Fin')


def refine_rock(mesh, main=False):
    r = random.Random(710 if main else 711)
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    if main:
        result = bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=1, use_grid_fill=True)
        # New mid-edge points add restrained relief; the approved summit stays fixed.
        for v in result['geom_inner']:
            if isinstance(v, bmesh.types.BMVert) and .08 < v.co.z < 1.56:
                v.co.x += r.uniform(-.014, .014)
                v.co.y += r.uniform(-.014, .014)
    else:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=.015, segments=1, affect='EDGES')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh); bm.free(); mesh.update()
    for p in mesh.polygons:
        center = sum((mesh.vertices[i].co for i in p.vertices), Vector()) / len(p.vertices)
        z = center.z
        path = center.y < -.10 and abs(center.x + .22 * math.sin(z * 5)) < .38
        # A meandering front trail and small shelves, rather than white rings.
        if p.normal.z > .83 and .1 < z < 1.22 and (path or not main):
            p.material_index = C['sand']
        else:
            patch = math.sin(center.x * 3.8 + center.y * 4.2 + z * 3)
            p.material_index = C['rock_light' if patch > .86 or p.normal.z > .78 else 'rock_dark' if patch < -.93 else 'rock']
        p.use_smooth = False


def refine_sand(mesh):
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=3, use_grid_fill=True)
    for v in bm.verts:
        edge_distance = max(0, 1 - math.sqrt((v.co.x / 2.25) ** 2 + (v.co.y / 1.8) ** 2))
        v.co.z = -.012 * edge_distance * (.5 + .5 * math.sin(v.co.x * 5 + v.co.y * 4))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh); bm.free()
    for p in mesh.polygons:
        p.material_index = C['sand']
        p.use_smooth = True


def build_palette(scene, output_path):
    """Write a real sRGB PNG and point every UV polygon into one padded swatch."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pixels = bytearray()
    for row in range(64):
        pixels.append(0)
        for col in range(64):
            index = (7 - row // 8) * 8 + col // 8
            value = SWATCHES[index][1] if index < len(SWATCHES) else '3A5BA0'
            pixels.extend(bytes.fromhex(value) + b'\xff')
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    output_path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', 64, 64, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b''))
    image = bpy.data.images.load(str(output_path), check_existing=False)
    image.name = 'Reef_Palette_64'
    image.colorspace_settings.name = 'sRGB'
    image.pack()
    material = bpy.data.materials.new('Reef_Palette')
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = .55
    bsdf.inputs['Metallic'].default_value = 0
    tex = material.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image, tex.interpolation = image, 'Closest'
    material.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    meshes = {obj.data for obj in scene.objects if obj.type == 'MESH'}
    for mesh in meshes:
        indices = [polygon.material_index for polygon in mesh.polygons]
        mesh.materials.clear()
        mesh.materials.append(material)
        uv = mesh.uv_layers.new(name='PaletteUV')
        for polygon, index in zip(mesh.polygons, indices):
            u, v = ((index % 8) + .5) / 8, ((index // 8) + .5) / 8
            for loop in polygon.loop_indices:
                uv.data[loop].uv = (u, v)
            polygon.material_index = 0
    return material
