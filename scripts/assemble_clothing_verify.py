import argparse
import bpy
import json
import os
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='Embed the lightweight rig and verify both detail rigs.')
parser.add_argument('--high', default=str(ROOT/'models'/'蓝发动漫少女·服装配色精修.blend'))
parser.add_argument('--low', default=str(ROOT/'models'/'蓝发动漫少女·服装配色精修轻量版.blend'))
parser.add_argument('--report', default=str(ROOT/'docs'/'clothing_validation.json'))
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
HIGH = os.path.abspath(args.high)
LOW = os.path.abspath(args.low)
REPORT = os.path.abspath(args.report)
os.makedirs(os.path.dirname(REPORT), exist_ok=True)
DETAILS = ['Detail_Eye_Catchlights', 'Detail_Eyelashes', 'Detail_Lips', 'Detail_Hair_Fibers', 'Detail_Clothing_Straps']
LOW_NAMES = ['BlueGirl_Preview_Polished', 'Rig_Bust_Hair', *DETAILS]

bpy.ops.wm.open_mainfile(filepath=HIGH)
scene = bpy.context.scene
old = bpy.data.collections.get('Preview_Lightweight_Hidden')
if old:
    for obj in list(old.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(old)

with bpy.data.libraries.load(LOW, link=False) as (source, target):
    target.objects = [name for name in LOW_NAMES if name in source.objects]
collection = bpy.data.collections.new('Preview_Lightweight_Hidden')
scene.collection.children.link(collection)
for obj in target.objects:
    if obj:
        collection.objects.link(obj)
        base_name = obj.name.rsplit('.', 1)[0] if obj.name.rsplit('.', 1)[-1].isdigit() else obj.name
        obj.name = 'Low_' + base_name

scene.frame_set(1)
report = {'high': {}, 'low': {}}
for prefix, key in [('', 'high'), ('Low_', 'low')]:
    arm = bpy.data.objects[prefix + 'Rig_Bust_Hair']
    report[key]['bones'] = len(arm.data.bones)
    report[key]['bone_names'] = [bone.name for bone in arm.data.bones]
    report[key]['weights'] = {}
    for name in DETAILS:
        obj = bpy.data.objects[prefix + name]
        sums = [sum(group.weight for group in vertex.groups) for vertex in obj.data.vertices]
        report[key]['weights'][name] = {'vertices': len(sums), 'min': min(sums), 'max': max(sums)}

names = [name for name in DETAILS] + ['Low_' + name for name in DETAILS]
snapshots = {name: {} for name in names}
for frame in (1, 31, 61):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    for name in names:
        obj = bpy.data.objects[name]
        evaluated = obj.evaluated_get(deps)
        stride = max(1, len(evaluated.data.vertices) // 1200)
        snapshots[name][frame] = np.array(
            [tuple(vertex.co) for vertex in list(evaluated.data.vertices)[::stride]],
            dtype=np.float64,
        )
for name in names:
    key = 'low' if name.startswith('Low_') else 'high'
    plain = name[4:] if key == 'low' else name
    report[key].setdefault('motion', {})[plain] = {}
    for frame in (31, 61):
        delta = np.linalg.norm(snapshots[name][frame] - snapshots[name][1], axis=1)
        report[key]['motion'][plain][str(frame)] = {'max': float(delta.max()), 'mean': float(delta.mean())}

scene['Polish_Notes'] = 'Eyes, lashes, lips, skin and silk hair retained from the facial polish pass.'
scene['Clothing_Notes'] = 'Reference 1793988150.8468552.jpeg used only for cool white-blue cloth and one navy diagonal shoulder strap. No headphones, guitar, or full-body geometry.'
scene['Rig_Notes'] = '18 bones. Facial details are head-weighted; hair fibers inherit hair weights; clothing strap inherits only Cloth_Cotton vertex weights. Lightweight rig is hidden in Preview_Lightweight_Hidden.'
scene.frame_set(1)
for obj in collection.objects:
    obj.hide_render = True
    obj.hide_set(True)
scene.camera = bpy.data.objects['Hero_Camera']
bpy.ops.wm.save_as_mainfile(filepath=HIGH)
with open(REPORT, 'w', encoding='utf-8') as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
print('COMBINED_BLEND', HIGH, os.path.getsize(HIGH), flush=True)
