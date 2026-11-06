import bpy
import math
import os
from mathutils import Vector

INPUT = '/mnt/agents/output/app/public/model.glb'
OUT = '/mnt/agents/output/app/src'

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=INPUT)

meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
arms = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
for obj in meshes:
    print('MESH', obj.name, 'verts', len(obj.data.vertices), 'polys', len(obj.data.polygons), 'bounds', [tuple(v) for v in obj.bound_box])
for arm in arms:
    print('ARMATURE', arm.name)
    for b in arm.data.bones:
        print('BONE', b.name, 'head', tuple(round(x, 5) for x in b.head_local), 'tail', tuple(round(x, 5) for x in b.tail_local), 'parent', b.parent.name if b.parent else None)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world.color = (0.2, 0.2, 0.2)
scene.world.use_nodes = True
scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value = (0.68, 0.75, 0.84, 1)
scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value = 0.55
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'

for mat in bpy.data.materials:
    if mat.use_nodes:
        p = mat.node_tree.nodes.get('Principled BSDF')
        if p:
            p.inputs['Roughness'].default_value = 0.58

def area(name, loc, energy, size, color):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector((0, 0, 0.15)) - obj.location).to_track_quat('-Z', 'Y').to_euler()

area('Key', (3, -4, 5), 450, 4, (1.0, 0.90, 0.84))
area('Fill', (-4, -1, 2), 260, 3, (0.72, 0.84, 1.0))
area('Rim', (0, 4, 4), 500, 3, (0.78, 0.88, 1.0))

cam_data = bpy.data.cameras.new('Camera')
cam = bpy.data.objects.new('Camera', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.clip_start = 0.005
cam_data.clip_end = 100
cam_data.lens = 58

forward = Vector((1.0, -1.0, 0.0)).normalized()
right = Vector((1.0, 1.0, 0.0)).normalized()

shots = {
    'diagnostic_hero': (Vector((0, 0, 0.02)), forward * 2.3 + right * 1.2 + Vector((0, 0, 0.42)), 52),
    'diagnostic_front': (Vector((0, 0, 0.14)), forward * 2.0 + Vector((0, 0, 0.18)), 58),
    'diagnostic_face': (Vector((0, 0, 0.245)), forward * 0.85 + right * 0.16 + Vector((0, 0, 0.08)), 66),
}
for name, (target, offset, lens) in shots.items():
    cam.location = target + offset
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam_data.lens = lens
    scene.render.filepath = os.path.join(OUT, name + '.png')
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'diagnostic.blend'))
