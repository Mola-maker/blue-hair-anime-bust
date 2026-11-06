import bpy
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath='/mnt/agents/output/app/src/diagnostic.blend')
scene = bpy.context.scene
cam = scene.camera
forward = Vector((1.0, -1.0, 0.0)).normalized()
base_target = Vector((0.0, 0.0, 0.14))
cam.location = base_target + forward * 2.0 + Vector((0, 0, 0.18))
cam.rotation_euler = (base_target - cam.location).to_track_quat('-Z', 'Y').to_euler()
q = cam.rotation_euler.to_quaternion()
cam_right = q @ Vector((1, 0, 0))
cam_up = q @ Vector((0, 1, 0))
target = base_target + cam_right * 0.016 - cam_up * 0.047
cam.location = target + forward * 1.02 + Vector((0, 0, 0.092))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = 58
scene.render.resolution_x = 1100
scene.render.resolution_y = 1100
scene.cycles.samples = 32
scene.render.filepath = '/mnt/agents/output/app/src/face_closeup.png'
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath='/mnt/agents/output/app/src/face_diagnostic.blend')
