import bpy
import math
import os
import random
import sys
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
MODE = ARGS[0] if ARGS else 'low'
IS_HIGH = MODE == 'high'
INPUT = '/mnt/agents/output/app/public/model-hires.glb' if IS_HIGH else '/mnt/agents/output/app/public/model.glb'
OUTPUT_GLB = '/mnt/agents/output/蓝发动漫少女·面部精修版.glb' if IS_HIGH else '/mnt/agents/output/蓝发动漫少女·面部精修轻量版.glb'
OUTPUT_BLEND = '/mnt/agents/output/app/蓝发动漫少女·面部精修.blend' if IS_HIGH else '/mnt/agents/output/app/src/low_polished.blend'
ROOT = '/mnt/agents/output/app/src'
random.seed(20261107)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=INPUT)
scene = bpy.context.scene
scene.frame_set(1)
base = max((o for o in bpy.context.scene.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
base.name = 'BlueGirl_High_Polished' if IS_HIGH else 'BlueGirl_Preview_Polished'
for obj in list(bpy.context.scene.objects):
    if obj not in (base, arm):
        obj.hide_render = True
        obj.hide_set(True)

# Material utilities.
def set_input(node, name, value):
    socket = node.inputs.get(name)
    if socket is not None:
        socket.default_value = value

def linear_hex(value):
    value = value.lstrip('#')
    rgb = [int(value[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb) + (1.0,)

original = base.data.materials[0]
original.name = 'Cloth_Cotton'
materials = [original]

def variant(name, roughness, specular=0.35, coat=0.0, subsurface=0.0, anisotropy=0.0, micro=False):
    mat = original.copy()
    mat.name = name
    p = mat.node_tree.nodes.get('Principled BSDF')
    set_input(p, 'Roughness', roughness)
    set_input(p, 'Metallic', 0.0)
    set_input(p, 'Specular IOR Level', specular)
    set_input(p, 'Coat Weight', coat)
    set_input(p, 'Coat Roughness', max(0.12, roughness * 0.65))
    set_input(p, 'Subsurface Weight', subsurface)
    set_input(p, 'Subsurface Radius', (1.0, 0.42, 0.24))
    set_input(p, 'Subsurface Scale', 0.006)
    set_input(p, 'Anisotropic IOR Level', anisotropy)
    set_input(p, 'Anisotropic', anisotropy)
    if micro:
        nt = mat.node_tree
        old_normal = p.inputs['Normal'].links[0].from_socket if p.inputs['Normal'].is_linked else None
        noise = nt.nodes.new('ShaderNodeTexNoise')
        noise.name = name + '_Microtexture'
        noise.inputs['Scale'].default_value = 760.0 if subsurface else 210.0
        noise.inputs['Detail'].default_value = 2.0
        bump = nt.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.075 if subsurface else 0.11
        bump.inputs['Distance'].default_value = 0.00010 if subsurface else 0.00016
        nt.links.new(noise.outputs['Fac'], bump.inputs['Height'])
        if old_normal:
            nt.links.new(old_normal, bump.inputs['Normal'])
        nt.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    materials.append(mat)
    return mat

skin_mat = variant('Skin_Soft', 0.49, 0.30, 0.035, 0.075, 0.0, True)
hair_mat = variant('Hair_Silk', 0.31, 0.43, 0.20, 0.0, 0.62, True)
pink_mat = variant('Hair_Pink_Silk', 0.34, 0.40, 0.16, 0.0, 0.52, True)
eye_mat = variant('Eye_Iris_Gloss', 0.16, 0.50, 0.48)
lash_base_mat = variant('Lash_Base_Matte', 0.42, 0.30, 0.06)
p = original.node_tree.nodes.get('Principled BSDF')
set_input(p, 'Roughness', 0.72)
set_input(p, 'Specular IOR Level', 0.26)
for mat in materials:
    if mat.name not in [m.name for m in base.data.materials]:
        base.data.materials.append(mat)
mat_index = {m.name: i for i, m in enumerate(base.data.materials)}

# Classify the single original atlas into cloth, skin, hair, pink accents and eyes.
verts = np.empty(len(base.data.vertices) * 3, dtype=np.float32)
base.data.vertices.foreach_get('co', verts)
verts = verts.reshape((-1, 3))
loop_count = len(base.data.loops)
loop_verts = np.empty(loop_count, dtype=np.int32)
base.data.loops.foreach_get('vertex_index', loop_verts)
loop_uv = np.empty(loop_count * 2, dtype=np.float32)
base.data.uv_layers.active.data.foreach_get('uv', loop_uv)
loop_uv = loop_uv.reshape((-1, 2))
loop_totals = np.empty(len(base.data.polygons), dtype=np.int32)
base.data.polygons.foreach_get('loop_total', loop_totals)
if not np.all(loop_totals == 3):
    raise RuntimeError('Expected triangulated source mesh')
centers = verts[loop_verts.reshape((-1, 3))].mean(axis=1)
uv_centers = loop_uv.reshape((-1, 3, 2)).mean(axis=1)
rgb = np.fromfile(os.path.join(ROOT, 'basecolor_1024.rgb'), dtype=np.uint8).reshape((1024, 1024, 3))
xs = np.clip((uv_centers[:, 0] * 1023).astype(np.int32), 0, 1023)
ys = np.clip(((1.0 - uv_centers[:, 1]) * 1023).astype(np.int32), 0, 1023)
colors = rgb[ys, xs].astype(np.float32) / 255.0
r, g, b = colors[:, 0], colors[:, 1], colors[:, 2]
luma = r * 0.25 + g * 0.55 + b * 0.20
skin = (r > 0.42) & (r > g * 1.015) & (g > b * 0.94) & (r > b * 1.025) & ((r-g) < 0.28)
pink = (r > b * 1.025) & (b > g * 1.045) & ((r-g) > 0.15)
hair = ((b > r * 1.035) & (b > g * 1.003)) | pink
forward2d = np.array([2**-0.5, -(2**-0.5), 0.0], dtype=np.float32)
face_zone = (centers[:, 2] > -0.082) & (centers[:, 2] < 0.078) & ((centers * forward2d).sum(axis=1) > 0.115)
eye = face_zone & (((b > r * 1.025) & (b > g * 0.94) & (r < 0.70)) | ((luma < 0.22) & (b > r * 0.98)))
lash_base = face_zone & (luma < 0.34) & (~eye)
indices = np.zeros(len(centers), dtype=np.int32)
indices[skin] = mat_index['Skin_Soft']
indices[hair] = mat_index['Hair_Silk']
indices[pink] = mat_index['Hair_Pink_Silk']
indices[eye] = mat_index['Eye_Iris_Gloss']
indices[lash_base] = mat_index['Lash_Base_Matte']
base.data.polygons.foreach_set('material_index', indices)
base.data.update()
bpy.context.view_layer.update()
print('MATERIAL_COUNTS', {base.data.materials[i].name: int((indices == i).sum()) for i in range(len(base.data.materials))}, flush=True)

# New detail materials.
def simple_material(name, color, roughness, specular=0.35, coat=0.0, emission=0.0, anisotropy=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    p = mat.node_tree.nodes.get('Principled BSDF')
    rgba = linear_hex(color)
    p.inputs['Base Color'].default_value = rgba
    set_input(p, 'Roughness', roughness)
    set_input(p, 'Metallic', 0.0)
    set_input(p, 'Specular IOR Level', specular)
    set_input(p, 'Coat Weight', coat)
    set_input(p, 'Coat Roughness', 0.18)
    set_input(p, 'Anisotropic IOR Level', anisotropy)
    set_input(p, 'Anisotropic', anisotropy)
    if emission:
        set_input(p, 'Emission Color', rgba)
        set_input(p, 'Emission Strength', emission)
    return mat

lash_mat = simple_material('Lash_Definition', '281923', 0.34, 0.38, 0.10)
lower_lash_mat = simple_material('Lash_Lower_Soft', '503443', 0.46, 0.28)
catch_mat = simple_material('Eye_Catchlight', 'F4FCFF', 0.12, 0.52, 0.40, 0.55)
catch_small_mat = simple_material('Eye_Catchlight_Cyan', 'C9F2FF', 0.16, 0.45, 0.30, 0.28)
lip_seam_mat = simple_material('Lip_Seam', '813D4C', 0.40, 0.28)
lip_mat = simple_material('Lip_Soft', 'DF929E', 0.27, 0.40, 0.34, 0.0)
lip_glint_mat = simple_material('Lip_Glint', 'FFE5E2', 0.18, 0.42, 0.35, 0.08)
hair_fiber_mats = [
    simple_material('Hair_Fiber_Light', '94CCF0', 0.28, 0.44, 0.20, 0.0, 0.70),
    simple_material('Hair_Fiber_Mid', '5793C8', 0.32, 0.40, 0.16, 0.0, 0.66),
    simple_material('Hair_Fiber_Dark', '285781', 0.36, 0.35, 0.12, 0.0, 0.60),
    simple_material('Hair_Fiber_Pink', 'E9A1C2', 0.32, 0.40, 0.18, 0.0, 0.62),
]

# Diagnostic cameras and surface ray sampling.
forward = Vector((1.0, -1.0, 0.0)).normalized()
right = Vector((1.0, 1.0, 0.0)).normalized()

def camera(name, target, offset, lens):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = target + offset
    obj.rotation_euler = (target - obj.location).to_track_quat('-Z', 'Y').to_euler()
    data.lens = lens
    data.clip_start = 0.002
    data.clip_end = 100
    return obj

base_target = Vector((0, 0, 0.14))
initial = camera('Face_Setup', base_target, forward * 2.0 + Vector((0, 0, 0.18)), 58)
q = initial.rotation_euler.to_quaternion()
cam_right = q @ Vector((1, 0, 0))
cam_up = q @ Vector((0, 1, 0))
face_target = base_target + cam_right * 0.016 - cam_up * 0.047
face_cam = camera('Detail_Eyes_Camera', face_target, forward * 1.02 + Vector((0, 0, 0.092)), 58)
bpy.data.objects.remove(initial, do_unlink=True)
q = face_cam.rotation_euler.to_quaternion()
old_target = face_cam.location + (q @ Vector((0, 0, -1))) * 1.0316
mouth_target = old_target - (q @ Vector((0, 1, 0))) * 0.128
mouth_cam = camera('Detail_Lips_Camera', mouth_target, forward * 0.72 + Vector((0, 0, 0.065)), 58)
scene.render.resolution_x = 1100
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()

def ray(cam, px, py, size=1100):
    frame = cam.data.view_frame(scene=scene)
    min_x, max_x = min(v.x for v in frame), max(v.x for v in frame)
    min_y, max_y = min(v.y for v in frame), max(v.y for v in frame)
    depth = abs(frame[0].z)
    local = Vector((min_x + px / size * (max_x-min_x), max_y - py / size * (max_y-min_y), -depth))
    direction = (cam.matrix_world.to_quaternion() @ local).normalized()
    hit, loc, normal, face, obj, matrix = scene.ray_cast(deps, cam.matrix_world.translation, direction, distance=10)
    if not hit or obj != base:
        return None
    return loc.copy(), normal.normalized(), int(face)

def smooth_pixels(points, subdivisions=5):
    pts = [Vector(p) for p in points]
    result = []
    for i in range(len(pts)-1):
        p0 = pts[max(0, i-1)]
        p1 = pts[i]
        p2 = pts[i+1]
        p3 = pts[min(len(pts)-1, i+2)]
        for j in range(subdivisions):
            t = j / subdivisions
            v = 0.5 * ((2*p1) + (-p0+p2)*t + (2*p0-5*p1+4*p2-p3)*t*t + (-p0+3*p1-3*p2+p3)*t*t*t)
            result.append(v)
    result.append(pts[-1])
    return result

def surface_path(cam, pixels, allowed, size=1100, smooth=5):
    result = []
    for pixel in smooth_pixels(pixels, smooth):
        hit = ray(cam, pixel.x, pixel.y, size)
        if hit and int(indices[hit[2]]) in allowed:
            result.append(hit)
    return result

skin_or_dark = {mat_index['Cloth_Cotton'], mat_index['Skin_Soft'], mat_index['Eye_Iris_Gloss'], mat_index['Lash_Base_Matte']}
hair_allowed = {mat_index['Hair_Silk'], mat_index['Hair_Pink_Silk']}
L_upper = surface_path(face_cam, [(305,715),(332,707),(364,713),(397,731),(428,752),(455,779)], skin_or_dark)
R_upper = surface_path(face_cam, [(832,833),(858,826),(888,831),(921,841),(956,854),(992,867)], skin_or_dark)
L_crease = surface_path(face_cam, [(315,692),(350,687),(388,701),(421,723)], skin_or_dark)
R_crease = surface_path(face_cam, [(835,807),(869,801),(905,811),(941,826)], skin_or_dark)
lip_seam = surface_path(mouth_cam, [(343,943),(376,949),(409,962),(443,978),(474,989)], skin_or_dark, 1000)
lower_lip = surface_path(mouth_cam, [(361,960),(388,968),(417,980),(445,989)], skin_or_dark, 1000)

lash_spikes = []
for pixels in [
    [(425,748),(446,735)], [(443,766),(468,754)], [(458,782),(485,779)],
    [(945,849),(968,830)], [(968,858),(996,844)], [(987,866),(1018,861)],
]:
    path = surface_path(face_cam, pixels, skin_or_dark, smooth=4)
    if len(path) >= 2:
        lash_spikes.append(path)
lower_lashes = []
for pixels in [
    [(377,839),(382,850)], [(397,832),(405,843)], [(418,820),(428,830)],
    [(861,939),(865,952)], [(882,934),(889,946)], [(902,925),(912,937)],
]:
    path = surface_path(face_cam, pixels, skin_or_dark, smooth=3)
    if len(path) >= 2:
        lower_lashes.append(path)

catchlights = []
for name, pixel, radius, small in [
    ('L_main', (330,785), 0.00345, False), ('L_small', (363,813), 0.00140, True),
    ('R_main', (788,905), 0.00365, False), ('R_small', (814,920), 0.00145, True),
]:
    hit = ray(face_cam, *pixel)
    if hit and int(indices[hit[2]]) not in hair_allowed:
        catchlights.append((name, hit, radius, small))
    else:
        print('CATCHLIGHT_REJECTED', name, flush=True)

lip_glint = ray(mouth_cam, 409, 974, 1000)

# Fine, deliberate flow lines on the visible bangs.
bang_paths = []
bang_pixel_paths = [
    [(105,40),(160,120),(215,215),(265,315),(295,420)],
    [(205,20),(260,105),(320,200),(365,300),(390,405)],
    [(365,15),(410,105),(445,215),(455,330),(425,455)],
    [(490,10),(485,125),(455,255),(405,390),(340,525)],
    [(555,0),(555,120),(530,260),(490,405),(440,545)],
    [(690,0),(700,130),(700,275),(685,425),(665,590),(640,740)],
    [(760,0),(770,140),(775,295),(770,450),(750,610),(720,770)],
    [(850,0),(865,130),(880,275),(890,425),(885,580),(860,720)],
    [(945,10),(955,135),(970,280),(980,430),(970,590)],
    [(1020,40),(1015,165),(1010,300),(1015,445),(1035,565)],
    [(80,330),(135,405),(180,495),(200,590),(180,690)],
    [(180,500),(230,555),(275,625),(300,705)],
]
for i, pixels in enumerate(bang_pixel_paths):
    path = surface_path(face_cam, pixels, hair_allowed, smooth=5)
    if len(path) >= 4:
        bang_paths.append((path, 0 if i % 4 == 0 else 1))

# Seeded short fibers follow the actual hair surface all around the bust.
hair_polys = [p for p in base.data.polygons if p.material_index in hair_allowed and p.center.z > -0.30]
short_fibers = []
for strand_i in range(210 if IS_HIGH else 160):
    if not hair_polys:
        break
    poly = random.choice(hair_polys)
    start = base.matrix_world @ poly.center
    normal = (base.matrix_world.to_3x3() @ poly.normal).normalized()
    hit = ray_from = None
    hit, loc, norm, face, obj, matrix = scene.ray_cast(deps, start + normal * 0.012, -normal, distance=0.03)
    if not hit or obj != base or int(indices[face]) not in hair_allowed:
        continue
    tangent = Vector((0, 0, -1)) - norm * norm.dot(Vector((0, 0, -1)))
    if tangent.length < 0.05:
        tangent = norm.cross(Vector((1, 0, 0)))
    tangent.normalize()
    points = [(loc + norm * 0.00038, norm.copy(), face)]
    step = random.uniform(0.0025, 0.0045)
    for j in range(random.randint(5, 9)):
        candidate = loc + tangent * step
        hit, new_loc, new_norm, new_face, obj, matrix = scene.ray_cast(deps, candidate + norm * 0.009, -norm, distance=0.022)
        if not hit or obj != base or int(indices[new_face]) not in hair_allowed:
            break
        loc, norm, face = new_loc, new_norm.normalized(), new_face
        points.append((loc + norm * 0.00038, norm.copy(), face))
        tangent = tangent - norm * tangent.dot(norm)
        if tangent.length < 0.01:
            break
        tangent.normalize()
    if len(points) >= 4:
        short_fibers.append((points, strand_i))

print('SURFACE_PATHS', {'L_upper':len(L_upper),'R_upper':len(R_upper),'lip':len(lip_seam),'bangs':len(bang_paths),'fibers':len(short_fibers),'catchlights':len(catchlights)}, flush=True)

# Mesh builders for tapered tubes and flattened catchlights.
class Builder:
    def __init__(self, name, mats):
        self.name, self.mats = name, mats
        self.verts, self.faces, self.face_mats = [], [], []
    def tube(self, path, radii, mat=0, sides=7):
        if len(path) < 2:
            return
        points = [p[0] for p in path]
        normals = [p[1] for p in path]
        if isinstance(radii, (float, int)):
            radii = [radii] * len(points)
        offset = len(self.verts)
        for i, (point, normal) in enumerate(zip(points, normals)):
            tangent = points[min(i+1,len(points)-1)] - points[max(i-1,0)]
            if tangent.length < 1e-8:
                tangent = Vector((0,0,1))
            tangent.normalize()
            side = tangent.cross(normal)
            if side.length < 0.01:
                side = tangent.cross(Vector((0,0,1)))
            if side.length < 0.01:
                side = tangent.cross(Vector((0,1,0)))
            side.normalize()
            up = tangent.cross(side).normalized()
            for j in range(sides):
                angle = 2 * math.pi * j / sides
                v = point + radii[i] * (side * math.cos(angle) + up * math.sin(angle))
                self.verts.append(tuple(v))
        for i in range(len(points)-1):
            for j in range(sides):
                self.faces.append((offset+i*sides+j, offset+i*sides+(j+1)%sides, offset+(i+1)*sides+(j+1)%sides, offset+(i+1)*sides+j))
                self.face_mats.append(mat)
        self.faces.append(tuple(offset+j for j in reversed(range(sides))))
        self.face_mats.append(mat)
        self.faces.append(tuple(offset+(len(points)-1)*sides+j for j in range(sides)))
        self.face_mats.append(mat)
    def ellipsoid(self, center, normal, rx, ry, rz, mat=0, segments=24, rings=12):
        normal = normal.normalized()
        u = normal.cross(Vector((0,0,1)))
        if u.length < 0.05:
            u = normal.cross(Vector((0,1,0)))
        u.normalize()
        v = normal.cross(u).normalized()
        offset = len(self.verts)
        for i in range(rings+1):
            phi = math.pi * i / rings
            for j in range(segments):
                theta = 2 * math.pi * j / segments
                p = center + u * (rx * math.sin(phi) * math.cos(theta)) + v * (ry * math.sin(phi) * math.sin(theta)) + normal * (rz * math.cos(phi))
                self.verts.append(tuple(p))
        for i in range(rings):
            for j in range(segments):
                self.faces.append((offset+i*segments+j, offset+i*segments+(j+1)%segments, offset+(i+1)*segments+(j+1)%segments, offset+(i+1)*segments+j))
                self.face_mats.append(mat)
    def finish(self):
        mesh = bpy.data.meshes.new(self.name + '_Mesh')
        mesh.from_pydata(self.verts, [], self.faces)
        mesh.update()
        obj = bpy.data.objects.new(self.name, mesh)
        scene.collection.objects.link(obj)
        for mat in self.mats:
            mesh.materials.append(mat)
        for p, mi in zip(mesh.polygons, self.face_mats):
            p.material_index = mi
            p.use_smooth = True
        return obj

lash_builder = Builder('Detail_Eyelashes', [lash_mat, lower_lash_mat])
for path in (L_upper, R_upper):
    n = len(path)
    if n > 1:
        profile = [0.00052 + 0.00035 * math.sin(math.pi*i/(n-1)) for i in range(n)]
        profile[0] *= 0.35
        profile[-1] *= 0.25
        lash_builder.tube(path, profile, 0, 8)
for path in (L_crease, R_crease):
    if len(path) > 1:
        lash_builder.tube(path, [0.00020]*len(path), 1, 6)
for path in lash_spikes:
    lash_builder.tube(path, [0.00062*(1-i/(len(path)-1))+0.00004 for i in range(len(path))], 0, 7)
for path in lower_lashes:
    lash_builder.tube(path, [0.00028*(1-i/(len(path)-1))+0.000025 for i in range(len(path))], 1, 6)
lash_obj = lash_builder.finish()

catch_builder = Builder('Detail_Eye_Catchlights', [catch_mat, catch_small_mat])
for name, hit, radius, small in catchlights:
    loc, normal, face = hit
    catch_builder.ellipsoid(loc + normal * 0.00075, normal, radius, radius*0.76, 0.00032, 1 if small else 0)
catch_obj = catch_builder.finish()

lip_builder = Builder('Detail_Lips', [lip_seam_mat, lip_mat, lip_glint_mat])
if len(lip_seam) > 1:
    lip_builder.tube(lip_seam, [0.00012 + 0.00034*math.sin(math.pi*i/(len(lip_seam)-1)) for i in range(len(lip_seam))], 0, 8)
if len(lower_lip) > 1:
    lip_builder.tube(lower_lip, [0.00010 + 0.00058*math.sin(math.pi*i/(len(lower_lip)-1)) for i in range(len(lower_lip))], 1, 8)
if lip_glint and int(indices[lip_glint[2]]) not in hair_allowed:
    loc, normal, face = lip_glint
    lip_builder.ellipsoid(loc + normal*0.00065, normal, 0.00095, 0.00042, 0.00020, 2, 20, 10)
lip_obj = lip_builder.finish()

hair_builder = Builder('Detail_Hair_Fibers', hair_fiber_mats)
for path, mi in bang_paths:
    n = len(path)
    radii = [0.00007 + 0.00013*math.sin(math.pi*i/(n-1)) for i in range(n)]
    hair_builder.tube(path, radii, mi, 6)
for path, strand_i in short_fibers:
    n = len(path)
    source_mat = int(indices[path[0][2]])
    mi = 3 if source_mat == mat_index['Hair_Pink_Silk'] else (0 if strand_i % 5 == 0 else (1 if strand_i % 5 in (1,2) else 2))
    radii = [0.000045 + 0.00012*math.sin(math.pi*i/(n-1)) for i in range(n)]
    hair_builder.tube(path, radii, mi, 5)
hair_obj = hair_builder.finish()
print('DETAIL_VERTS', {o.name:len(o.data.vertices) for o in (lash_obj,catch_obj,lip_obj,hair_obj)}, flush=True)

# Facial details follow the head exactly; hair fibers inherit only nearby hair weights.
for obj in (lash_obj, catch_obj, lip_obj):
    obj.parent = arm
    group = obj.vertex_groups.new(name='head')
    group.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
    mod = obj.modifiers.new('Rig_Bust_Hair', 'ARMATURE')
    mod.object = arm
    mod.use_deform_preserve_volume = False
hair_vertex_ids = sorted({v for p in hair_polys for v in p.vertices})
kd = KDTree(len(hair_vertex_ids))
for vertex_id in hair_vertex_ids:
    kd.insert(base.matrix_world @ base.data.vertices[vertex_id].co, vertex_id)
kd.balance()
cache = {}
hair_obj.parent = arm
group_names = [g.name for g in base.vertex_groups]
groups = {name: hair_obj.vertex_groups.new(name=name) for name in group_names}
for v in hair_obj.data.vertices:
    co, index, distance = kd.find(hair_obj.matrix_world @ v.co)
    if index not in cache:
        cache[index] = [(base.vertex_groups[g.group].name, g.weight) for g in base.data.vertices[index].groups if g.weight > 0.0001]
    weights = cache[index] or [('head', 1.0)]
    total = sum(w for _, w in weights)
    for name, weight in weights:
        groups[name].add([v.index], weight/total, 'REPLACE')
mod = hair_obj.modifiers.new('Rig_Bust_Hair', 'ARMATURE')
mod.object = arm
mod.use_deform_preserve_volume = False

# Studio lighting and final camera setup.
scene.world.use_nodes = True
scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value = (0.68, 0.75, 0.84, 1)
scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value = 0.55
scene.render.engine = 'CYCLES'
scene.cycles.samples = 40
scene.cycles.use_denoising = True
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'

def area(name, loc, energy, size, color):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector((0,0,0.10))-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj
area('Key_Softbox', (3,-4,5), 450, 4, (1.0,0.90,0.84))
area('Fill_Softbox', (-4,-1,2), 260, 3, (0.72,0.84,1.0))
area('Rim_Softbox', (0,4,4), 500, 3, (0.78,0.88,1.0))
hero_cam = camera('Hero_Camera', Vector((0,0,0.02)), forward*2.3 + right*1.2 + Vector((0,0,0.42)), 52)
scene.camera = hero_cam
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000

# Select only deliverable meshes and their rig for glTF.
bpy.ops.object.select_all(action='DESELECT')
base.select_set(True)
arm.select_set(True)
for obj in (lash_obj, catch_obj, lip_obj, hair_obj):
    obj.select_set(True)
bpy.context.view_layer.objects.active = base
bpy.ops.export_scene.gltf(
    filepath=OUTPUT_GLB,
    export_format='GLB',
    use_selection=True,
    export_animations=True,
    export_skins=True,
    export_all_influences=False,
    export_extras=True,
    export_yup=True,
    export_apply=False,
)
print('EXPORTED', OUTPUT_GLB, os.path.getsize(OUTPUT_GLB), flush=True)

if IS_HIGH:
    scene.camera = face_cam
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 1100
    scene.cycles.samples = 48
    scene.render.filepath = '/mnt/agents/output/蓝发动漫少女·眼部精修.png'
    bpy.ops.render.render(write_still=True)
    scene.camera = mouth_cam
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.cycles.samples = 40
    scene.render.filepath = '/mnt/agents/output/蓝发动漫少女·唇肤精修.png'
    bpy.ops.render.render(write_still=True)
    scene.camera = hero_cam
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 1100
    scene.render.filepath = '/mnt/agents/output/蓝发动漫少女·整体精修预览.png'
    bpy.ops.render.render(write_still=True)

scene.camera = hero_cam
bpy.ops.object.select_all(action='DESELECT')
base.select_set(True)
bpy.context.view_layer.objects.active = base
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
print('SAVED', OUTPUT_BLEND, flush=True)
