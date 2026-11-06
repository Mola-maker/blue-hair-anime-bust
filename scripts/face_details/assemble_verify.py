import bpy
import numpy as np
import os

HIGH = '/mnt/agents/output/app/蓝发动漫少女·面部精修.blend'
LOW = '/mnt/agents/output/app/src/low_polished.blend'
bpy.ops.wm.open_mainfile(filepath=HIGH)
scene = bpy.context.scene

# Keep the lightweight, independently rigged version inside the editable project.
low_names = ['BlueGirl_Preview_Polished','Rig_Bust_Hair','Detail_Eye_Catchlights','Detail_Eyelashes','Detail_Hair_Fibers','Detail_Lips']
with bpy.data.libraries.load(LOW, link=False) as (source, target):
    target.objects = [name for name in low_names if name in source.objects]
collection = bpy.data.collections.new('Preview_Lightweight_Hidden')
scene.collection.children.link(collection)
for obj in target.objects:
    if obj:
        collection.objects.link(obj)
        obj.name = 'Low_' + obj.name
        obj.hide_render = True
        obj.hide_set(True)

scene['Polish_Notes'] = 'Eyes: paired catchlights; tapered upper/lower lashes; conformed lip seam and lower-lip sheen; seeded surface hair fibers; independent skin/hair/iris/cloth PBR.'
scene['Rig_Notes'] = '18 bones retained. Facial details head-weighted; hair fibers weighted from nearest hair vertices. Lightweight version is hidden in Preview_Lightweight_Hidden.'
scene.frame_set(1)
high_arm = bpy.data.objects['Rig_Bust_Hair']
print('HIGH_BONES', len(high_arm.data.bones), [b.name for b in high_arm.data.bones], flush=True)

names = ['BlueGirl_High_Polished','Detail_Eye_Catchlights','Detail_Eyelashes','Detail_Lips','Detail_Hair_Fibers']
for name in names[1:]:
    obj = bpy.data.objects[name]
    sums = []
    for v in obj.data.vertices:
        sums.append(sum(g.weight for g in v.groups))
    print('WEIGHTS', name, len(sums), min(sums), max(sums), flush=True)

snapshots = {name:{} for name in names}
for frame in (1,31,61):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    for name in names:
        obj = bpy.data.objects[name]
        evaluated = obj.evaluated_get(deps)
        stride = max(1, len(evaluated.data.vertices)//1200)
        snapshots[name][frame] = np.array([tuple(v.co) for v in list(evaluated.data.vertices)[::stride]], dtype=np.float64)
for name in names:
    for frame in (31,61):
        delta = np.linalg.norm(snapshots[name][frame]-snapshots[name][1],axis=1)
        print('MOTION',name,frame,'max',float(delta.max()),'mean',float(delta.mean()),flush=True)

scene.frame_set(61)
scene.camera = bpy.data.objects['Detail_Eyes_Camera']
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.cycles.samples = 32
scene.render.filepath = '/mnt/agents/output/app/src/action_face_61.png'
bpy.ops.render.render(write_still=True)
scene.frame_set(1)
scene.camera = bpy.data.objects['Hero_Camera']
bpy.ops.wm.save_as_mainfile(filepath=HIGH)
print('COMBINED_BLEND', os.path.getsize(HIGH), flush=True)
