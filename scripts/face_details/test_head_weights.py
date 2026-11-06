import bpy
bpy.ops.wm.open_mainfile(filepath='/mnt/agents/output/app/蓝发动漫少女·面部精修.blend')
scene=bpy.context.scene
arm=bpy.data.objects['Rig_Bust_Hair']
for name in ['Detail_Eye_Catchlights','Detail_Eyelashes','Detail_Lips']:
 obj=bpy.data.objects[name]
 obj.parent=arm
 obj.vertex_groups.clear()
 group=obj.vertex_groups.new(name='head')
 group.add(list(range(len(obj.data.vertices))),1.0,'REPLACE')
bpy.data.objects['Detail_Hair_Fibers'].parent=arm
scene.frame_set(2); scene.frame_set(1)
scene.camera=bpy.data.objects['Detail_Eyes_Camera']
scene.render.resolution_x=1100; scene.render.resolution_y=1100
scene.cycles.samples=32
scene.render.filepath='/mnt/agents/output/app/src/head_weight_test.png'
bpy.ops.render.render(write_still=True)
