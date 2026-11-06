import argparse
import bpy
import math
import os
from pathlib import Path
import sys
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree

parser=argparse.ArgumentParser(description='Apply cool white-blue cloth and a rigged navy strap.')
parser.add_argument('mode',choices=['high','low'])
parser.add_argument('--input',required=True,help='Facial-polish Blender checkpoint')
parser.add_argument('--output-blend',required=True)
parser.add_argument('--output-glb',required=True)
parser.add_argument('--render-dir',default=str(Path(__file__).resolve().parents[1]/'previews'))
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
HIGH=args.mode=='high'
INPUT=os.path.abspath(args.input)
OUTPUT_BLEND=os.path.abspath(args.output_blend)
OUTPUT_GLB=os.path.abspath(args.output_glb)
RENDER_DIR=os.path.abspath(args.render_dir)
os.makedirs(RENDER_DIR,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=INPUT)
scene=bpy.context.scene
scene.frame_set(1)
base=bpy.data.objects['BlueGirl_High_Polished' if HIGH else 'BlueGirl_Preview_Polished']
arm=bpy.data.objects['Rig_Bust_Hair']
cloth=bpy.data.materials['Cloth_Cotton']

# Cool white-blue cloth from the new reference, without changing skin or hair.
nt=cloth.node_tree
p=nt.nodes.get('Principled BSDF')
p.inputs['Roughness'].default_value=0.68
if p.inputs.get('Sheen Weight'):
    p.inputs['Sheen Weight'].default_value=0.14
if p.inputs.get('Sheen Roughness'):
    p.inputs['Sheen Roughness'].default_value=0.62
if p.inputs['Base Color'].is_linked:
    source=p.inputs['Base Color'].links[0].from_socket
    mix=nt.nodes.new('ShaderNodeMixRGB')
    mix.name='Reference_Cool_White'
    mix.blend_type='MULTIPLY'
    mix.inputs[0].default_value=1.0
    mix.inputs[2].default_value=(0.94,0.975,1.0,1.0)
    nt.links.new(source,mix.inputs[1])
    nt.links.new(mix.outputs[0],p.inputs['Base Color'])

def rgba(hex_color):
    h=hex_color.lstrip('#')
    cs=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(c/12.92 if c<=0.04045 else ((c+.055)/1.055)**2.4 for c in cs)+(1,)

def material(name,color,roughness):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=rgba(color)
    p.inputs['Roughness'].default_value=roughness
    p.inputs['Metallic'].default_value=0
    if p.inputs.get('Coat Weight'): p.inputs['Coat Weight'].default_value=0.07
    return m
strap_mat=material('Cloth_Strap_Navy','17243D',0.48)
edge_mat=material('Cloth_Strap_Edge','506681',0.52)

# Reuse the clothing diagnostic camera.
forward=Vector((1,-1,0)).normalized()
right=Vector((1,1,0)).normalized()
cam=bpy.data.objects['Hero_Camera']
target=Vector((0,0,-0.245))
cam.location=target+forward*1.35+right*0.10+Vector((0,0,0.12))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.lens=58
scene.camera=cam
scene.render.resolution_x=1000
scene.render.resolution_y=1000
bpy.context.view_layer.update()
deps=bpy.context.evaluated_depsgraph_get()
cloth_index=next(i for i,m in enumerate(base.data.materials) if m.name=='Cloth_Cotton')
cloth_vertex_ids=sorted({v for p in base.data.polygons if p.material_index==cloth_index for v in p.vertices})
cloth_vertex_map={old:new for new,old in enumerate(cloth_vertex_ids)}
cloth_coords=[base.matrix_world@base.data.vertices[v].co for v in cloth_vertex_ids]
cloth_faces=[tuple(cloth_vertex_map[v] for v in p.vertices) for p in base.data.polygons if p.material_index==cloth_index]
cloth_bvh=BVHTree.FromPolygons(cloth_coords,cloth_faces,all_triangles=False)

def ray(px,py):
    frame=cam.data.view_frame(scene=scene)
    min_x,max_x=min(v.x for v in frame),max(v.x for v in frame)
    min_y,max_y=min(v.y for v in frame),max(v.y for v in frame)
    local=Vector((min_x+px/1000*(max_x-min_x),max_y-py/1000*(max_y-min_y),-abs(frame[0].z)))
    direction=(cam.matrix_world.to_quaternion()@local).normalized()
    inv=base.matrix_world.inverted()
    origin=inv@cam.matrix_world.translation
    local_direction=(inv.to_3x3()@direction).normalized()
    # Raycast only the base mesh and pass through hair/skin until white cloth is found.
    # Separate detail objects cannot interrupt the strap; real hair still occludes it in renders.
    for _ in range(12):
        hit,loc,normal,face=base.ray_cast(origin,local_direction,distance=10,depsgraph=deps)
        if not hit:
            return None
        if base.data.polygons[face].material_index==cloth_index:
            world=base.matrix_world@loc
            world_normal=(base.matrix_world.to_3x3()@normal).normalized()
            return world,world_normal,face
        origin=loc+local_direction*.0015
    return None

def smooth(points,steps=6):
    pts=[Vector(p) for p in points]
    out=[]
    for i in range(len(pts)-1):
        p0,p1,p2,p3=pts[max(0,i-1)],pts[i],pts[i+1],pts[min(len(pts)-1,i+2)]
        for j in range(steps):
            t=j/steps
            out.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
    out.append(pts[-1])
    return out

def surface(points):
    result=[]
    for px,py in smooth(points):
        hit=ray(px,py)
        if hit: result.append(hit)
    return result

paths=[
    (surface([(650,600),(620,660),(580,730),(540,800),(500,875)])[3:],0.022),
]
paths=[p for p in paths if len(p[0])>=4]
print('STRAP_PATHS',[len(p[0]) for p in paths],flush=True)

verts=[]; faces=[]; face_mats=[]; edge_paths=[]
cross_steps=6
for path,width in paths:
    offset=len(verts)
    left_edge=[]; right_edge=[]
    for i,(loc,normal,face) in enumerate(path):
        tangent=path[min(i+1,len(path)-1)][0]-path[max(i-1,0)][0]
        tangent.normalize()
        side=tangent.cross(normal).normalized()
        taper=0.76+0.24*math.sin(math.pi*i/(len(path)-1))
        row=[]
        for j in range(cross_steps):
            across=(j/(cross_steps-1)-.5)*width*taper
            candidate=loc+side*across
            nearest,nearest_normal,nearest_face,_=cloth_bvh.find_nearest(candidate)
            if nearest is None:
                nearest,nearest_normal=loc,normal
            point=nearest+nearest_normal*.00085
            row.append((point,nearest_normal,face))
            verts.append(tuple(point))
        left_edge.append(row[0]); right_edge.append(row[-1])
    for i in range(len(path)-1):
        for j in range(cross_steps-1):
            a=offset+i*cross_steps+j
            faces.append((a,a+1,a+1+cross_steps,a+cross_steps)); face_mats.append(0)
    edge_paths.extend([left_edge,right_edge])

def add_tube(path,radius,mat_index=1,sides=6):
    offset=len(verts)
    for i,(loc,normal,face) in enumerate(path):
        tangent=path[min(i+1,len(path)-1)][0]-path[max(i-1,0)][0]
        tangent.normalize()
        side=tangent.cross(normal).normalized()
        up=tangent.cross(side).normalized()
        for j in range(sides):
            a=2*math.pi*j/sides
            verts.append(tuple(loc+radius*(side*math.cos(a)+up*math.sin(a))))
    for i in range(len(path)-1):
        for j in range(sides):
            faces.append((offset+i*sides+j,offset+i*sides+(j+1)%sides,offset+(i+1)*sides+(j+1)%sides,offset+(i+1)*sides+j)); face_mats.append(mat_index)
for path in edge_paths:
    if len(path)>=2: add_tube(path,0.00042)

mesh=bpy.data.meshes.new('Clothing_Straps_Mesh')
mesh.from_pydata(verts,[],faces); mesh.update()
obj=bpy.data.objects.new('Detail_Clothing_Straps',mesh)
scene.collection.objects.link(obj)
mesh.materials.append(strap_mat); mesh.materials.append(edge_mat)
for poly,mi in zip(mesh.polygons,face_mats):
    poly.material_index=mi; poly.use_smooth=True

# Inherit only cloth-surface weights, avoiding nearby hair or skin influences.
kd=KDTree(len(cloth_vertex_ids))
for vid in cloth_vertex_ids: kd.insert(base.matrix_world@base.data.vertices[vid].co,vid)
kd.balance()
groups={g.name:obj.vertex_groups.new(name=g.name) for g in base.vertex_groups}
cache={}
for v in mesh.vertices:
    _,idx,_=kd.find(v.co)
    if idx not in cache:
        cache[idx]=[(base.vertex_groups[g.group].name,g.weight) for g in base.data.vertices[idx].groups if g.weight>0.0001]
    weights=cache[idx] or [('chest',1.0)]
    total=sum(w for _,w in weights)
    for name,w in weights: groups[name].add([v.index],w/total,'REPLACE')
mod=obj.modifiers.new('Rig_Bust_Hair','ARMATURE'); mod.object=arm
obj.parent=arm

# Export only the corresponding high or low rigged set.
bpy.ops.object.select_all(action='DESELECT')
base.select_set(True); arm.select_set(True); obj.select_set(True)
for name in ['Detail_Eye_Catchlights','Detail_Eyelashes','Detail_Hair_Fibers','Detail_Lips']:
    bpy.data.objects[name].select_set(True)
bpy.context.view_layer.objects.active=base
bpy.ops.export_scene.gltf(filepath=OUTPUT_GLB,export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIVE_ACTIONS',export_skins=True,export_all_influences=False,export_yup=True,export_apply=False)
print('EXPORTED',OUTPUT_GLB,os.path.getsize(OUTPUT_GLB),flush=True)

if HIGH:
    scene.cycles.samples=40
    scene.render.filepath=os.path.join(RENDER_DIR,'蓝发动漫少女·服装配色精修.png')
    bpy.ops.render.render(write_still=True)
    hero=bpy.data.objects['Hero_Camera']
    target=Vector((0,0,0.02))
    hero.location=target+forward*2.3+Vector((1,1,0)).normalized()*1.2+Vector((0,0,0.42))
    hero.rotation_euler=(target-hero.location).to_track_quat('-Z','Y').to_euler()
    hero.data.lens=52
    scene.render.resolution_x=1100; scene.render.resolution_y=1100
    scene.render.filepath=os.path.join(RENDER_DIR,'蓝发动漫少女·服装配色整体预览.png')
    bpy.ops.render.render(write_still=True)
scene['Clothing_Reference']='1793988150.8468552.jpeg: cool white-blue top and navy shoulder straps only; no headphones, guitar, or full-body geometry.'
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
print('SAVED',OUTPUT_BLEND,flush=True)
