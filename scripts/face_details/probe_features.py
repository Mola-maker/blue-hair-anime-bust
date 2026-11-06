import bpy
from mathutils import Vector
from mathutils.geometry import barycentric_transform

bpy.ops.wm.open_mainfile(filepath='/mnt/agents/output/app/src/face_diagnostic.blend')
scene = bpy.context.scene
cam = scene.camera
deps = bpy.context.evaluated_depsgraph_get()
W = scene.render.resolution_x
H = scene.render.resolution_y
frame = cam.data.view_frame(scene=scene)
min_x = min(v.x for v in frame)
max_x = max(v.x for v in frame)
min_y = min(v.y for v in frame)
max_y = max(v.y for v in frame)
depth = abs(frame[0].z)

points = {
    'L_iris_main': (330, 785), 'L_iris_small': (363, 813),
    'R_iris_main': (788, 905), 'R_iris_small': (814, 920),
    'L_lash_0': (290, 721), 'L_lash_1': (325, 704), 'L_lash_2': (365, 709),
    'L_lash_3': (405, 731), 'L_lash_4': (442, 760), 'L_lash_5': (465, 786),
    'R_lash_0': (817, 835), 'R_lash_1': (850, 824), 'R_lash_2': (887, 828),
    'R_lash_3': (926, 840), 'R_lash_4': (965, 853), 'R_lash_5': (1007, 867),
}
for name, (px, py) in points.items():
    local = Vector((min_x + (px / W) * (max_x-min_x), max_y - (py / H) * (max_y-min_y), -depth))
    direction = (cam.matrix_world.to_quaternion() @ local).normalized()
    origin = cam.matrix_world.translation
    hit, loc, normal, face, obj, matrix = scene.ray_cast(deps, origin, direction, distance=10)
    if not hit:
        print(name, 'NO_HIT')
        continue
    uv = None
    ev = obj.evaluated_get(deps)
    me = ev.data
    if face < len(me.polygons) and me.uv_layers.active:
        poly = me.polygons[face]
        if len(poly.vertices) >= 3:
            ids = list(poly.vertices)[:3]
            uv = barycentric_transform(loc, me.vertices[ids[0]].co, me.vertices[ids[1]].co, me.vertices[ids[2]].co,
                                       Vector((*me.uv_layers.active.data[poly.loop_start].uv, 0)),
                                       Vector((*me.uv_layers.active.data[poly.loop_start+1].uv, 0)),
                                       Vector((*me.uv_layers.active.data[poly.loop_start+2].uv, 0)))
    print(name, 'pos', tuple(round(v, 6) for v in loc), 'normal', tuple(round(v, 4) for v in normal), 'obj', obj.name, 'face', face, 'uv', tuple(round(v, 5) for v in uv) if uv else None)
