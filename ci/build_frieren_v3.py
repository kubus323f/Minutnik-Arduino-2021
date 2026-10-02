import bpy
import importlib
import math
import os
import sys
from mathutils import Vector

ROOT = os.getcwd()
OUT = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)

# ---------- MPFB2 dynamic imports ----------
def dynamic_import(suffix, key):
    for name in list(sys.modules):
        if name.endswith(suffix):
            mod = importlib.import_module(name)
            if hasattr(mod, key):
                return getattr(mod, key)
    raise RuntimeError(f"No module ending {suffix} with {key}")

HumanService = dynamic_import("mpfb.services.humanservice", "HumanService")
TargetService = dynamic_import("mpfb.services.targetservice", "TargetService")
LocationService = dynamic_import("mpfb.services.locationservice", "LocationService")

# ---------- helpers ----------
def mat(name, color, rough=0.5, metal=0.0, sss=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*color, 1.0)
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Metallic"].default_value = metal
    if "Subsurface Weight" in bs.inputs:
        bs.inputs["Subsurface Weight"].default_value = sss
    return m

def smooth(obj):
    if obj.type == 'MESH':
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj

def safe_target(human, category, filename, weight):
    path = os.path.join(LocationService.get_mpfb_data("targets"), category, filename + ".target.gz")
    if os.path.exists(path):
        print("TARGET", category, filename, weight)
        TargetService.load_target(human, path, weight=weight)
        return True
    print("TARGET_MISSING", path)
    return False

def create_mesh(name, verts, faces, material=None, subdiv=1, solidify=None, bevel=None):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if material:
        obj.data.materials.append(material)
    smooth(obj)
    if solidify:
        mod = obj.modifiers.new("Solidify", "SOLIDIFY")
        mod.thickness = solidify
        mod.offset = 0.0
    if bevel:
        mod = obj.modifiers.new("MicroBevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    if subdiv:
        mod = obj.modifiers.new("Subdivision", "SUBSURF")
        mod.levels = subdiv
        mod.render_levels = subdiv
    return obj

def loft(name, rings, segments, material, pleats=0, subdiv=1, solidify=0.002):
    verts, faces = [], []
    for z, rx, ry, phase_amp in rings:
        for j in range(segments):
            a = 2 * math.pi * j / segments
            wave = 1.0 + (phase_amp * math.cos(pleats * a) if pleats else 0.0)
            verts.append((rx * wave * math.cos(a), ry * wave * math.sin(a), z))
    nr = len(rings)
    for r in range(nr - 1):
        for j in range(segments):
            a = r * segments + j
            b = r * segments + (j + 1) % segments
            c = (r + 1) * segments + (j + 1) % segments
            d = (r + 1) * segments + j
            faces.append((a, b, c, d))
    return create_mesh(name, verts, faces, material, subdiv=subdiv, solidify=solidify, bevel=0.0007)

def open_cape(name, rings, material, segments=88, gap_deg=34):
    # open at the front (-Y, angle -90 degrees)
    amin = math.radians(-90 + gap_deg)
    amax = math.radians(270 - gap_deg)
    verts, faces = [], []
    for z, rx, ry in rings:
        for j in range(segments + 1):
            a = amin + (amax - amin) * j / segments
            verts.append((rx * math.cos(a), ry * math.sin(a), z))
    cols = segments + 1
    for r in range(len(rings) - 1):
        for j in range(segments):
            a = r * cols + j
            faces.append((a, a + 1, a + 1 + cols, a + cols))
    return create_mesh(name, verts, faces, material, subdiv=2, solidify=0.003, bevel=0.001)

def sweep(name, points, radii, material, segments=28, subdiv=1):
    points = [Vector(p) for p in points]
    verts, faces = [], []
    prev_n1 = None
    for i, p in enumerate(points):
        if i == 0:
            t = (points[1] - p).normalized()
        elif i == len(points) - 1:
            t = (p - points[i - 1]).normalized()
        else:
            t = (points[i + 1] - points[i - 1]).normalized()
        ref = Vector((0, 1, 0))
        if abs(t.dot(ref)) > 0.92:
            ref = Vector((0, 0, 1))
        n1 = t.cross(ref).normalized()
        if prev_n1 and n1.dot(prev_n1) < 0:
            n1 = -n1
        n2 = t.cross(n1).normalized()
        prev_n1 = n1
        rx, ry = radii[i] if isinstance(radii[i], tuple) else (radii[i], radii[i])
        for j in range(segments):
            a = 2 * math.pi * j / segments
            q = p + n1 * (rx * math.cos(a)) + n2 * (ry * math.sin(a))
            verts.append(tuple(q))
    for r in range(len(points) - 1):
        for j in range(segments):
            a = r * segments + j
            b = r * segments + (j + 1) % segments
            c = (r + 1) * segments + (j + 1) % segments
            d = (r + 1) * segments + j
            faces.append((a, b, c, d))
    return create_mesh(name, verts, faces, material, subdiv=subdiv, solidify=None, bevel=0.0007)

def ribbon(name, points, widths, material, thickness=0.0014):
    points = [Vector(p) for p in points]
    verts, faces = [], []
    for i, p in enumerate(points):
        if i == 0:
            t = (points[1] - points[0]).normalized()
        elif i == len(points) - 1:
            t = (points[-1] - points[-2]).normalized()
        else:
            t = (points[i + 1] - points[i - 1]).normalized()
        side = t.cross(Vector((0, 1, 0)))
        if side.length < 1e-5:
            side = t.cross(Vector((0, 0, 1)))
        side.normalize()
        w = widths[i]
        verts.append(tuple(p - side * w * 0.5))
        verts.append(tuple(p + side * w * 0.5))
    for i in range(len(points) - 1):
        a = i * 2
        faces.append((a, a + 1, a + 3, a + 2))
    return create_mesh(name, verts, faces, material, subdiv=2, solidify=thickness, bevel=0.0007)

def ellipsoid(name, loc, scale, material, seg=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    smooth(o)
    return o

def cube(name, loc, scale, material, bevel=0.004):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    smooth(o)
    if bevel:
        b = o.modifiers.new("Bevel", "BEVEL")
        b.width = bevel
        b.segments = 3
    return o

def world_bone_points(rig, names):
    pts = []
    for name in names:
        b = rig.data.bones.get(name)
        if b:
            if not pts:
                pts.append(rig.matrix_world @ b.head_local)
            pts.append(rig.matrix_world @ b.tail_local)
    return pts

def bind_auto(obj, rig):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    try:
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        print("BOUND", obj.name)
    except Exception as e:
        print("BIND_WARN", obj.name, repr(e))

def parent_to_bone(obj, rig, bone_name):
    if rig.data.bones.get(bone_name):
        obj.parent = rig
        obj.parent_type = 'BONE'
        obj.parent_bone = bone_name
        obj.matrix_parent_inverse = rig.matrix_world.inverted()

# ---------- clean scene ----------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# ---------- anatomical base ----------
macro = TargetService.get_default_macro_info_dict()
macro['gender'] = 0.0
macro['age'] = 0.28
macro['muscle'] = 0.24
macro['weight'] = 0.34
macro['height'] = 0.44
macro['proportions'] = 0.72
if 'cupsize' in macro:
    macro['cupsize'] = 0.24
if 'firmness' in macro:
    macro['firmness'] = 0.68
if 'race' in macro:
    macro['race']['caucasian'] = 0.74
    macro['race']['asian'] = 0.26
    macro['race']['african'] = 0.0

human = HumanService.create_human(mask_helpers=True, detailed_helpers=True, extra_vertex_groups=True, feet_on_ground=True, scale=0.1, macro_detail_dict=macro)
human.name = 'Frieren_Anatomy'

# Frieren-like facial proportions: still anatomically plausible, but slightly stylized.
for side in ('l', 'r'):
    safe_target(human, 'eyes', f'{side}-eye-scale-incr', 0.28)
    safe_target(human, 'eyes', f'{side}-eye-height2-incr', 0.14)
    safe_target(human, 'eyes', f'{side}-eye-eyefold-up', 0.10)
safe_target(human, 'nose', 'nose-volume-decr', 0.38)
safe_target(human, 'nose', 'nose-scale-horiz-decr', 0.28)
safe_target(human, 'nose', 'nose-scale-vert-decr', 0.12)
safe_target(human, 'chin', 'chin-width-decr', 0.26)
safe_target(human, 'chin', 'chin-height-decr', 0.10)
safe_target(human, 'mouth', 'mouth-scale-horiz-decr', 0.10)

smooth(human)
sub = human.modifiers.new('Anatomy_Subdivision', 'SUBSURF')
sub.levels = 1
sub.render_levels = 2
rig = HumanService.add_builtin_rig(human, 'default')
rig.name = 'Frieren_Rig'

# Bounding box after targets
pts = [human.matrix_world @ Vector(c) for c in human.bound_box]
xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
xmin, xmax = min(xs), max(xs); ymin, ymax = min(ys), max(ys); zmin, zmax = min(zs), max(zs)
h = zmax - zmin
cy = (ymin + ymax) * 0.5
print('FINAL_BODY_BBOX', xmin, xmax, ymin, ymax, zmin, zmax, 'H', h)

# ---------- materials ----------
skin = mat('Skin_PaleWarm', (0.50, 0.30, 0.24), rough=0.53, sss=0.08)
white = mat('Frieren_White', (0.78, 0.77, 0.72), rough=0.52)
gold = mat('Frieren_Gold', (0.44, 0.28, 0.075), rough=0.38, metal=0.18)
black = mat('Frieren_Leggings', (0.025, 0.030, 0.050), rough=0.62)
brown = mat('Boot_Leather', (0.20, 0.095, 0.045), rough=0.48)
hairmat = mat('Silver_Hair', (0.63, 0.66, 0.76), rough=0.36)
hairhi = mat('Silver_Hair_Highlight', (0.82, 0.84, 0.90), rough=0.31)
eye_white = mat('Eye_Sclera', (0.86, 0.84, 0.80), rough=0.28)
iris_mat = mat('Iris_Green', (0.05, 0.30, 0.24), rough=0.24)
pupil_mat = mat('Pupil', (0.003, 0.006, 0.008), rough=0.2)
red = mat('Red_Gem', (0.42, 0.015, 0.02), rough=0.2, metal=0.05)

if len(human.data.materials) == 0:
    human.data.materials.append(skin)
else:
    for i in range(len(human.data.materials)):
        human.data.materials[i] = skin

# ---------- eyes: fit to face surface ----------
world_verts = [human.matrix_world @ v.co for v in human.data.vertices]
eye_z = zmin + h * 0.895
eye_x = h * 0.0335
for side, sx in [('L', -1), ('R', 1)]:
    ex = sx * eye_x
    candidates = [p for p in world_verts if abs(p.x - ex) < h * 0.022 and abs(p.z - eye_z) < h * 0.026]
    face_front = min((p.y for p in candidates), default=ymin + h * 0.15)
    center_y = face_front + h * 0.0125
    e = ellipsoid(f'Eye_{side}', (ex, center_y, eye_z), (h*0.0195, h*0.013, h*0.0155), eye_white, 56, 28)
    # Iris/pupil sit flush with the front of the eyeball (-Y)
    iris_y = center_y - h * 0.0130
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=h*0.0080, depth=h*0.0017, location=(ex, iris_y, eye_z), rotation=(math.pi/2, 0, 0))
    ir = bpy.context.object; ir.name=f'Iris_{side}'; ir.data.materials.append(iris_mat); smooth(ir)
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=h*0.0034, depth=h*0.0019, location=(ex, iris_y-h*0.0010, eye_z), rotation=(math.pi/2, 0, 0))
    pu = bpy.context.object; pu.name=f'Pupil_{side}'; pu.data.materials.append(pupil_mat); smooth(pu)
    parent_to_bone(e, rig, 'head')
    parent_to_bone(ir, rig, 'head')
    parent_to_bone(pu, rig, 'head')

# ---------- elf ears ----------
def elf_ear(side):
    sx = -1 if side == 'L' else 1
    zc = zmin + h * 0.895
    xb = sx * h * 0.061
    yt = cy - h * 0.010
    centers = []
    for t in (0.0, 0.22, 0.45, 0.68, 0.84, 1.0):
        x = xb + sx * h * (0.085 * t)
        y = yt + h * (0.007 * math.sin(math.pi*t))
        z = zc + h * (0.010 * math.sin(math.pi*t) - 0.005*t)
        centers.append(Vector((x,y,z)))
    verts, faces = [], []
    seg = 20
    for i,c in enumerate(centers):
        t = i/(len(centers)-1)
        ry = h*(0.015*(1-t)+0.0015)
        rz = h*(0.026*(1-t)+0.0020)
        for j in range(seg):
            a=2*math.pi*j/seg
            verts.append(tuple(c + Vector((0, ry*math.cos(a), rz*math.sin(a)))))
    for r in range(len(centers)-1):
        for j in range(seg):
            a=r*seg+j; b=r*seg+(j+1)%seg; c=(r+1)*seg+(j+1)%seg; d=(r+1)*seg+j
            faces.append((a,b,c,d))
    o=create_mesh('Elf_Ear_'+side, verts, faces, skin, subdiv=2, bevel=0.0005)
    parent_to_bone(o, rig, 'head')
    return o

ears=[elf_ear('L'), elf_ear('R')]

# red drop earrings
for sx, side in [(-1,'L'),(1,'R')]:
    x=sx*h*0.075; z=zmin+h*0.865; y=cy-h*0.005
    ellipsoid('Earring_'+side,(x,y,z),(h*.006,h*.004,h*.014),red,40,20)

# ---------- costume ----------
# Main robe / dress: shaped rather than a single cone, with gentle pleating at skirt.
dress = loft('Dress', [
    (zmin+h*.735, h*.150, h*.105, 0.000),
    (zmin+h*.700, h*.145, h*.100, 0.000),
    (zmin+h*.640, h*.128, h*.090, 0.000),
    (zmin+h*.585, h*.135, h*.094, 0.006),
    (zmin+h*.535, h*.165, h*.115, 0.012),
    (zmin+h*.480, h*.210, h*.145, 0.020),
    (zmin+h*.430, h*.245, h*.175, 0.028),
], 112, white, pleats=14, subdiv=2, solidify=h*.0020)

# gold hem band slightly outside dress
hem = loft('Gold_Hem', [
    (zmin+h*.438, h*.248, h*.178, 0.026),
    (zmin+h*.423, h*.250, h*.180, 0.027),
], 112, gold, pleats=14, subdiv=1, solidify=h*.0023)

# Capelet / shoulder mantle
cape = open_cape('Capelet', [
    (zmin+h*.795, h*.055, h*.045),
    (zmin+h*.775, h*.115, h*.080),
    (zmin+h*.735, h*.195, h*.125),
    (zmin+h*.690, h*.225, h*.145),
], white, 104, 30)
# cape gold trim
cape_trim = open_cape('Capelet_Gold_Trim', [
    (zmin+h*.697, h*.221, h*.142),
    (zmin+h*.685, h*.227, h*.148),
], gold, 104, 30)

# Neck collar and gem
bpy.ops.mesh.primitive_torus_add(major_radius=h*.040, minor_radius=h*.007, major_segments=64, minor_segments=16, location=(0,cy,zmin+h*.805))
collar=bpy.context.object; collar.name='Gold_Collar'; collar.scale=(1.0,0.78,1.0); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); collar.data.materials.append(gold); smooth(collar)
ellipsoid('Collar_Gem',(0,cy-h*.042,zmin+h*.802),(h*.011,h*.004,h*.012),red,40,20)

# striped front inset recognizable from reference
front_y = -h*.098
panel = cube('Chest_Panel',(0,front_y,zmin+h*.690),(h*.055,h*.003,h*.095),white,bevel=h*.002)
for iz in range(4):
    z=zmin+h*(.646 + iz*.031)
    cube(f'Chest_Stripe_{iz}',(0,front_y-h*.004,z),(h*.052,h*.002,h*.0075),black,bevel=h*.001)
# vertical gold edges to panel
for sx in (-1,1):
    cube('Panel_Gold_Edge_'+str(sx),(sx*h*.059,front_y-h*.005,zmin+h*.690),(h*.005,h*.0025,h*.100),gold,bevel=h*.001)

# Sleeves fitted along rig arms
for side in ('L','R'):
    armpts = world_bone_points(rig,[f'upperarm01.{side}',f'upperarm02.{side}',f'lowerarm01.{side}',f'lowerarm02.{side}',f'wrist.{side}'])
    if len(armpts) < 4:
        sx=-1 if side=='L' else 1
        armpts=[Vector((sx*h*.16,0,zmin+h*.74)),Vector((sx*h*.28,0,zmin+h*.66)),Vector((sx*h*.38,0,zmin+h*.56)),Vector((sx*h*.43,0,zmin+h*.54))]
    n=len(armpts)
    rs=[]
    for i in range(n):
        t=i/(n-1)
        r=h*(.046*(1-t)+.025*t)
        rs.append((r,r*.78))
    sl=sweep('Sleeve_'+side,armpts,rs,white,32,2)
    # cuff band from last two close points
    p=armpts[-1]; prev=armpts[-2]; d=(p-prev).normalized()
    c0=p-d*h*.035; c1=p-d*h*.008
    cuff=sweep('Gold_Cuff_'+side,[c0,c1],[(h*.030,h*.024),(h*.029,h*.023)],gold,32,1)

# dark leggings based on leg rig
for side in ('L','R'):
    legpts=world_bone_points(rig,[f'upperleg01.{side}',f'upperleg02.{side}',f'lowerleg01.{side}',f'lowerleg02.{side}',f'foot.{side}'])
    if len(legpts)<4:
        sx=-1 if side=='L' else 1
        legpts=[Vector((sx*h*.07,0,zmin+h*.50)),Vector((sx*h*.075,0,zmin+h*.32)),Vector((sx*h*.065,0,zmin+h*.12)),Vector((sx*h*.065,-h*.03,zmin+h*.04))]
    n=len(legpts); rs=[]
    for i in range(n):
        t=i/(n-1)
        r=h*(.050*(1-t)+.027*t)
        rs.append((r,r*.82))
    sweep('Legging_'+side,legpts,rs,black,34,2)

# boots with fitted shafts + rounded toes
for side,sx in [('L',-1),('R',1)]:
    legpts=world_bone_points(rig,[f'lowerleg01.{side}',f'lowerleg02.{side}',f'foot.{side}'])
    if len(legpts)>=3:
        ankle=legpts[-2]; foot=legpts[-1]; calf=legpts[max(0,len(legpts)-3)]
        shaft_top=calf.lerp(ankle,.42)
    else:
        ankle=Vector((sx*h*.065,0,zmin+h*.07)); foot=Vector((sx*h*.065,-h*.08,zmin+h*.035)); shaft_top=Vector((sx*h*.065,0,zmin+h*.22))
    sweep('Boot_Shaft_'+side,[shaft_top,shaft_top.lerp(ankle,.55),ankle],[(h*.040,h*.034),(h*.036,h*.031),(h*.034,h*.029)],brown,36,2)
    toe_center=foot + Vector((0,-h*.030,h*.010))
    ellipsoid('Boot_Foot_'+side,toe_center,(h*.043,h*.082,h*.030),brown,56,28)
    # cuff
    d=(ankle-shaft_top).normalized(); c1=shaft_top; c0=shaft_top+d*h*.022
    sweep('Boot_Cuff_'+side,[c1,c0],[(h*.046,h*.039),(h*.045,h*.038)],brown,36,1)

# ---------- hair ----------
head_c = Vector((0, cy+h*.002, zmin+h*.905))
rx,ry,rz=h*.072,h*.065,h*.090
# Scalp cap (upper ellipsoid only)
verts,faces=[],[]; latn=18; lonn=72
for i in range(latn+1):
    th=(math.pi*.52)*i/latn
    for j in range(lonn):
        ph=2*math.pi*j/lonn
        verts.append((head_c.x+rx*math.sin(th)*math.cos(ph),head_c.y+ry*math.sin(th)*math.sin(ph),head_c.z+rz*math.cos(th)))
for i in range(latn):
    for j in range(lonn):
        a=i*lonn+j; b=i*lonn+(j+1)%lonn; c=(i+1)*lonn+(j+1)%lonn; d=(i+1)*lonn+j
        faces.append((a,b,c,d))
cap=create_mesh('Hair_Scalp',verts,faces,hairmat,subdiv=2,solidify=h*.0013,bevel=h*.0005)
parent_to_bone(cap,rig,'head')

# bangs and side framing locks
bang_specs=[
    (-.050,[(-.045,-.070,.955),(-.050,-.082,.920),(-.045,-.090,.875)],.032),
    (-.020,[(-.018,-.073,.966),(-.024,-.088,.925),(-.030,-.095,.885)],.034),
    (.012,[(.012,-.074,.965),(.010,-.090,.925),(.005,-.096,.890)],.030),
    (.043,[(.040,-.070,.955),(.047,-.083,.918),(.055,-.088,.880)],.030),
]
for idx,(_,coords,wf) in enumerate(bang_specs):
    ps=[(x*h,y*h,zmin+z*h) for x,y,z in coords]
    ribbon(f'Bang_{idx}',ps,[h*wf,h*(wf*.85),h*.010],hairhi if idx%2 else hairmat,h*.0015)

# long side/twin-tail hair cards; many overlapping ribbons for volume
for side,sx in [('L',-1),('R',1)]:
    root=Vector((sx*h*.066,cy+h*.020,zmin+h*.925))
    for k in range(10):
        lateral=(k-4.5)*h*.006
        depth=((k%3)-1)*h*.006
        p0=root+Vector((lateral,depth,0))
        p1=Vector((sx*h*(.105+.004*k),cy+h*(.022+.004*(k%2)),zmin+h*.805))
        p2=Vector((sx*h*(.125+.004*k),cy+h*(.030+.004*(k%3)),zmin+h*.650))
        p3=Vector((sx*h*(.105+.006*k),cy+h*(.040+.003*(k%2)),zmin+h*(.485-.006*k)))
        widths=[h*.022,h*.030,h*.034,h*.008]
        ribbon(f'Tail_{side}_{k}',[p0,p1,p2,p3],widths,hairhi if k%3==0 else hairmat,h*.0013)
    # tie
    ellipsoid('HairTie_'+side,(sx*h*.072,cy+h*.020,zmin+h*.920),(h*.018,h*.012,h*.016),hairmat,40,20)

# two longer front locks
for side,sx in [('L',-1),('R',1)]:
    ps=[(sx*h*.060,cy-h*.052,zmin+h*.940),(sx*h*.083,cy-h*.062,zmin+h*.835),(sx*h*.090,cy-h*.045,zmin+h*.720)]
    ribbon('FrontLock_'+side,ps,[h*.026,h*.034,h*.008],hairhi,h*.0015)

# ---------- red/gold shoulder ornaments ----------
for sx,side in [(-1,'L'),(1,'R')]:
    ellipsoid('Shoulder_Gem_'+side,(sx*h*.145,cy-h*.010,zmin+h*.735),(h*.012,h*.007,h*.014),red,40,20)

# ---------- rigging / parenting ----------
for obj in [dress,hem,cape,cape_trim,panel]:
    bind_auto(obj,rig)
# obvious rigid head accessories
for obj in bpy.data.objects:
    if obj.name.startswith(('Bang_','Tail_','HairTie_','FrontLock_','Earring_','Collar_Gem','Gold_Collar','Shoulder_Gem_')):
        parent_to_bone(obj,rig,'head')

# ---------- ground / studio ----------
floor_mat=mat('Studio_Floor',(0.095,0.105,0.125),rough=.78)
bpy.ops.mesh.primitive_plane_add(size=7,location=(0,0,zmin-0.008)); floor=bpy.context.object; floor.name='StudioFloor'; floor.data.materials.append(floor_mat)

# ---------- camera/lights ----------
def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def area(name,loc,energy,size,target):
    bpy.ops.object.light_add(type='AREA',location=loc)
    o=bpy.context.object; o.name=name; o.data.energy=energy; o.data.shape='DISK'; o.data.size=size; aim(o,target); return o

focus=(0,cy,zmin+h*.58)
area('Key',(h*.75,ymin-h*.72,zmin+h*.93),210,2.2,focus)
area('Fill',(-h*.68,ymin-h*.35,zmin+h*.68),95,2.8,focus)
area('Rim',(0,ymax+h*.60,zmin+h*.92),170,1.8,focus)

bpy.ops.object.camera_add(location=(h*.58,ymin-h*1.42,zmin+h*.60))
cam=bpy.context.object; cam.name='Camera_3Q'; cam.data.lens=62; aim(cam,(0,cy,zmin+h*.57)); bpy.context.scene.camera=cam

scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=900; scene.render.resolution_y=1200; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGBA'; scene.render.image_settings.color_depth='8'
scene.render.film_transparent=False
scene.world.color=(0.012,0.014,0.020)
scene.view_settings.look='AgX - Medium High Contrast'; scene.view_settings.exposure=-0.45

# Render full body 3/4
scene.render.filepath=os.path.join(OUT,'frieren_v3_3q.png')
bpy.ops.render.render(write_still=True)

# Front full body
cam.location=(0,ymin-h*1.58,zmin+h*.60); cam.data.lens=64; aim(cam,(0,cy,zmin+h*.57))
scene.render.filepath=os.path.join(OUT,'frieren_v3_front.png')
bpy.ops.render.render(write_still=True)

# Face / upper-body validation render
cam.location=(h*.22,ymin-h*.70,zmin+h*.86); cam.data.lens=78; aim(cam,(0,cy-h*.01,zmin+h*.83))
scene.render.resolution_x=1000; scene.render.resolution_y=1000
scene.render.filepath=os.path.join(OUT,'frieren_v3_face.png')
bpy.ops.render.render(write_still=True)

# Save animation-ready scene
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'Frieren_v3_animation_ready.blend'))
print('FRIEREN_V3_OK',OUT)
