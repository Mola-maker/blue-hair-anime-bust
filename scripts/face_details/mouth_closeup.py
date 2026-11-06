import bpy
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath='/mnt/agents/output/app/src/face_diagnostic.blend')
scene = bpy.context.scene
cam = scene.camera
forward = Vector((1.0, -1.0, 0.0)).normalized()
q = cam.rotation_euler.to_quaternion()
cam_up = q @ Vector((0, 1, 0))
view_dir = q @ Vector((0, 0, -1))
old_target = cam.location + view_dir * 1.0316
target = old_target - cam_up * 0.128
cam.location = target + forward * 0.72 + Vector((0, 0, 0.065))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = 58
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.cycles.samples = 32
scene.render.filepath = '/mnt/agents/output/app/src/mouth_closeup.png'
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath='/mnt/agents/output/app/src/mouth_diagnostic.blend')
