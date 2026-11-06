import argparse
import bpy
import os
import sys
from mathutils import Vector

parser = argparse.ArgumentParser(description='Render the chest diagnostic camera.')
parser.add_argument('--input', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(args.input))
scene = bpy.context.scene
scene.frame_set(1)
forward = Vector((1, -1, 0)).normalized()
right = Vector((1, 1, 0)).normalized()
cam = bpy.data.objects['Hero_Camera']
target = Vector((0, 0, -0.245))
cam.location = target + forward * 1.35 + right * 0.10 + Vector((0, 0, 0.12))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = 58
scene.camera = cam
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.cycles.samples = 32
scene.render.filepath = os.path.abspath(args.output)
bpy.ops.render.render(write_still=True)
