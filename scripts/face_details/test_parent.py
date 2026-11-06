import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
bpy.ops.wm.open_mainfile(filepath='/mnt/agents/output/app/蓝发动漫少女·面部精修.blend')
scene=bpy.context.scene
arm=bpy.data.objects['Rig_Bust_Hair']
for name in ['Detail_Eye_Catchlights','Detail_Eyelashes','Detail_Lips','Detail_Hair_Fibers']:
 bpy.data.objects[name].parent=arm
scene.frame_set(2)
scene.frame_set(1)
bpy.context.view_layer.update()
deps=bpy.context.evaluated_depsgraph_get()
cam=bpy.data.objects['Detail_Eyes_Camera']; scene.camera=cam
scene.render.resolution_x=1100; scene.render.resolution_y=1100
catch=bpy.data.objects['Detail_Eye_Catchlights'].evaluated_get(deps)
for i in range(4):
 pts=[v.co for v in catch.data.vertices[i*312:(i+1)*312]]
 center=sum(pts,Vector())/len(pts)
 projected=world_to_camera_view(scene,cam,center)
 print('CENTER',i,tuple(center),'pixel',projected.x*1100,(1-projected.y)*1100)
frame=cam.data.view_frame(scene=scene); min_x,max_x=min(v.x for v in frame),max(v.x for v in frame); min_y,max_y=min(v.y for v in frame),max(v.y for v in frame); depth=abs(frame[0].z)
for name,(px,py) in {'L_main':(330,785),'R_main':(788,905)}.items():
 local=Vector((min_x+px/1100*(max_x-min_x),max_y-py/1100*(max_y-min_y),-depth)); direction=(cam.matrix_world.to_quaternion()@local).normalized()
 hit,loc,normal,face,obj,matrix=scene.ray_cast(deps,cam.matrix_world.translation,direction,distance=10)
 print(name,'hit',obj.name if hit else None)
scene.render.filepath='/mnt/agents/output/app/src/parent_test.png'
scene.cycles.samples=24
bpy.ops.render.render(write_still=True)
