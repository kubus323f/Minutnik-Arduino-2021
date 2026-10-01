import bpy, os, sys, math, traceback
from mathutils import Vector

ROOT = os.getcwd()
OUT = os.path.join(ROOT, 'out')
os.makedirs(OUT, exist_ok=True)
MPFB_SRC = os.path.join(ROOT, 'mpfb2', 'src')
if MPFB_SRC not in sys.path:
    sys.path.insert(0, MPFB_SRC)

import mpfb
mpfb.register()
from mpfb.services.humanservice import HumanService
from mpfb.services.targetservice import TargetService

def mat(name, base, rough=0.45, metallic=0.0, subsurface=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*base, 1)
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metallic
    if 'Subsurface Weight' in bs.inputs:
        bs.inputs['Subsurface Weight'].default_value = subsurface
    return m

def smooth(obj):
    if obj.type == 'MESH':
        for p in obj.data.polygons:
            p.use_smooth = True

def add_uv(name, loc, scale, material, seg=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth(o); o.data.materials.append(material)
    return o

def add_cylinder(name, loc, radius, depth, material, scale_xy=(1,1), rot=(0,0,0), vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rot)
    o=bpy.context.object; o.name=name; o.scale=(scale_xy[0], scale_xy[1], 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth(o); o.data.materials.append(material)
    bevel=o.modifiers.new('Bevel','BEVEL'); bevel.width=radius*0.08; bevel.segments=3
    return o

def add_curve(name, pts, radius, material, resolution=5):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'; cu.resolution_u=resolution
    cu.bevel_depth=radius; cu.bevel_resolution=4; cu.resolution_u=8
    sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
    for bp,co in zip(sp.bezier_points,pts):
        bp.co=co; bp.handle_left_type='AUTO'; bp.handle_right_type='AUTO'
    obj=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(obj); cu.materials.append(material)
    return obj

def add_ear(name, side, head_center, h, skin):
    sx = side
    cx,cy,cz=head_center
    base_x = cx + sx*0.071*h
    base_y = cy - 0.003*h
    base_z = cz + 0.008*h
    tip_x = cx + sx*0.145*h
    tip_y = cy + 0.006*h
    tip_z = cz + 0.016*h
    verts=[]
    outline=[
        (base_x, base_y, base_z-0.035*h),
        (cx+sx*0.095*h, base_y, base_z-0.018*h),
        (tip_x, tip_y, tip_z),
        (cx+sx*0.095*h, base_y, base_z+0.026*h),
        (base_x, base_y, base_z+0.035*h),
    ]
    t=0.006*h
    for yoff in (-t,t):
        for x,y,z in outline: verts.append((x,y+yoff,z))
    faces=[(0,1,2,3,4),(9,8,7,6,5)]
    for i in range(5):
        j=(i+1)%5; faces.append((i,j,5+j,5+i))
    me=bpy.data.meshes.new(name+'Mesh'); me.from_pydata(verts,[],faces); me.update()
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o); smooth(o); me.materials.append(skin)
    bev=o.modifiers.new('EarSoft','BEVEL'); bev.width=0.003*h; bev.segments=4
    sub=o.modifiers.new('EarSubsurf','SUBSURF'); sub.levels=2; sub.render_levels=2
    return o

def create_dress(center, h, white, gold, dark, brown):
    x0,y0,z0=center
    add_cylinder('UnderTunic',(x0,y0,z0+0.54*h),0.105*h,0.29*h,dark,(0.85,0.62),vertices=64)
    bpy.ops.mesh.primitive_cone_add(vertices=96, radius1=0.18*h, radius2=0.11*h, depth=0.38*h, location=(x0,y0,z0+0.51*h))
    dress=bpy.context.object; dress.name='Frieren_Ivory_Tunic'; smooth(dress); dress.data.materials.append(white)
    bev=dress.modifiers.new('TunicSoft','BEVEL'); bev.width=0.004*h; bev.segments=3
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, location=(x0,y0+0.006*h,z0+0.69*h))
    cape=bpy.context.object; cape.name='Frieren_Shoulder_Mantle'; cape.scale=(0.18*h,0.105*h,0.10*h)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); smooth(cape); cape.data.materials.append(white)
    add_cylinder('Black_Belt',(x0,y0,z0+0.49*h),0.116*h,0.028*h,dark,(1.0,0.67),vertices=96)
    for z,maj,minr in [(z0+0.32*h,0.178*h,0.006*h),(z0+0.73*h,0.115*h,0.004*h)]:
        bpy.ops.mesh.primitive_torus_add(major_radius=maj, minor_radius=minr, major_segments=96, minor_segments=12, location=(x0,y0,z), rotation=(0,0,0))
        tor=bpy.context.object; tor.name='Gold_Trim'; tor.scale=(1,0.66,1); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); tor.data.materials.append(gold); smooth(tor)
    for sx in (-1,1):
        x=x0+sx*0.052*h
        add_cylinder('Brown_Boot', (x,y0+0.003*h,z0+0.115*h),0.049*h,0.22*h,brown,(0.72,1.10),vertices=64)

def add_hair(head_center, h, silver, darksilver):
    cx,cy,cz=head_center
    for i in range(34):
        a=2*math.pi*i/34
        if math.sin(a) < -0.55 and i%2: continue
        rx=0.064*h*math.cos(a); ry=0.050*h*math.sin(a)
        start=(cx+rx, cy+ry+0.01*h, cz+0.055*h)
        mid=(cx+rx*1.15, cy+max(ry,0.0)+0.030*h, cz-0.13*h)
        end=(cx+rx*1.55, cy+0.035*h+0.5*ry, cz-0.38*h - (0.02*h if i%3==0 else 0))
        add_curve(f'Hair_Long_{i:02d}', [start,mid,end], 0.0085*h, silver if i%3 else darksilver)
    for i,xn in enumerate((-0.055,-0.038,-0.020,0,0.020,0.038,0.055)):
        x=cx+xn*h
        start=(x,cy-0.047*h,cz+0.060*h)
        mid=(x*0.92+cx*0.08,cy-0.057*h,cz+0.01*h)
        end=(cx+xn*0.72*h,cy-0.061*h,cz-0.052*h)
        add_curve(f'Hair_Fringe_{i}',[start,mid,end],0.009*h,silver)
    for sx in (-1,1):
        start=(cx+sx*0.062*h,cy+0.005*h,cz+0.015*h)
        mid=(cx+sx*0.105*h,cy+0.025*h,cz-0.12*h)
        end=(cx+sx*0.115*h,cy+0.035*h,cz-0.42*h)
        add_curve('Hair_SideTail_L' if sx<0 else 'Hair_SideTail_R',[start,mid,end],0.021*h,silver)
        add_uv('Hair_Tie',start,(0.018*h,0.018*h,0.018*h),darksilver,32,16)

for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
macro = TargetService.get_default_macro_info_dict()
for k,v in [('gender',1.0),('age',0.42),('muscle',0.42),('weight',0.38),('height',0.53),('proportions',0.58)]:
    if k in macro: macro[k]=v
if 'race' in macro and isinstance(macro['race'], dict):
    for k in list(macro['race'].keys()): macro['race'][k]=0.0
    if 'caucasian' in macro['race']: macro['race']['caucasian']=1.0

human = HumanService.create_human(mask_helpers=True,detailed_helpers=True,extra_vertex_groups=True,feet_on_ground=True,scale=0.1,macro_detail_dict=macro)
human.name='Frieren_Anatomical_Base'
smooth(human)
sub=human.modifiers.new('HighResolution','SUBSURF'); sub.subdivision_type='CATMULL_CLARK'; sub.levels=2; sub.render_levels=2
try:
    rig=HumanService.add_builtin_rig(human,'default')
    if rig: rig.name='Frieren_Animation_Rig'
except Exception as e:
    print('RIG_WARNING',repr(e))

corners=[human.matrix_world @ Vector(c) for c in human.bound_box]
minx=min(v.x for v in corners); maxx=max(v.x for v in corners)
miny=min(v.y for v in corners); maxy=max(v.y for v in corners)
minz=min(v.z for v in corners); maxz=max(v.z for v in corners)
h=maxz-minz; cx=(minx+maxx)/2; cy=(miny+maxy)/2
print('BODY_BBOX',minx,maxx,miny,maxy,minz,maxz,'H',h)

skin=mat('Skin',(0.74,0.48,0.39),rough=0.48,subsurface=0.09)
bs=skin.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(0.78,0.55,0.47,1)
human.data.materials.clear(); human.data.materials.append(skin)
white=mat('Ivory_Cloth',(0.80,0.77,0.68),rough=0.78)
gold=mat('Gold_Trim',(0.65,0.38,0.08),rough=0.30,metallic=0.55)
dark=mat('Dark_Cloth',(0.025,0.035,0.045),rough=0.72)
brown=mat('Boot_Leather',(0.20,0.08,0.035),rough=0.55)
silver=mat('Silver_Hair',(0.72,0.75,0.80),rough=0.32)
darksilver=mat('Hair_Shadow',(0.38,0.42,0.50),rough=0.38)
eye_white=mat('Eye_Sclera',(0.88,0.90,0.92),rough=0.22)
iris=mat('Iris_Green',(0.13,0.42,0.34),rough=0.18)
black=mat('Pupil',(0.005,0.008,0.008),rough=0.12)
head=(cx, cy-0.004*h, minz+0.895*h)
for sx in (-1,1):
    ex=cx+sx*0.027*h; ey=cy-0.061*h; ez=minz+0.902*h
    add_uv('Eye_L' if sx<0 else 'Eye_R',(ex,ey,ez),(0.018*h,0.012*h,0.013*h),eye_white,48,24)
    add_uv('Iris_L' if sx<0 else 'Iris_R',(ex,ey-0.0115*h,ez),(0.008*h,0.003*h,0.008*h),iris,32,16)
    add_uv('Pupil_L' if sx<0 else 'Pupil_R',(ex,ey-0.0142*h,ez),(0.003*h,0.0015*h,0.003*h),black,24,12)
add_ear('Elf_Ear_L',-1,head,h,skin); add_ear('Elf_Ear_R',1,head,h,skin)
add_hair(head,h,silver,darksilver)
create_dress((cx,cy,minz),h,white,gold,dark,brown)
red=mat('Garnet',(0.36,0.015,0.025),rough=0.25,metallic=0.15)
for sx in (-1,1):
    add_uv('Earring',(cx+sx*0.086*h,cy-0.007*h,minz+0.887*h),(0.008*h,0.005*h,0.014*h),red,32,16)

bpy.ops.mesh.primitive_plane_add(size=4*h, location=(cx,cy,minz-0.002*h)); ground=bpy.context.object; ground.name='Studio_Ground'; ground.data.materials.append(mat('Ground',(0.12,0.13,0.15),rough=0.9))
world=bpy.context.scene.world or bpy.data.worlds.new('World'); bpy.context.scene.world=world; world.use_nodes=True; world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.025,0.03,0.04,1); world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.24

def area(name,loc,energy,size,color):
    bpy.ops.object.light_add(type='AREA',location=loc); l=bpy.context.object; l.name=name; l.data.energy=energy; l.data.shape='DISK'; l.data.size=size; l.data.color=color
    direction=Vector((cx,cy,minz+0.62*h))-l.location; l.rotation_euler=direction.to_track_quat('-Z','Y').to_euler(); return l
area('Key',(cx-0.65*h,cy-0.9*h,minz+1.15*h),1500,0.65*h,(1.0,0.82,0.72))
area('Fill',(cx+0.75*h,cy-0.5*h,minz+0.8*h),900,0.55*h,(0.65,0.78,1.0))
area('Rim',(cx+0.35*h,cy+0.85*h,minz+1.0*h),1200,0.45*h,(0.78,0.85,1.0))

scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=900; scene.render.resolution_y=1200; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False; scene.render.image_settings.color_mode='RGBA'
scene.view_settings.look='AgX - Medium High Contrast'

def camera_render(name,loc,target,path,lens=58):
    bpy.ops.object.camera_add(location=loc); cam=bpy.context.object; cam.name=name; cam.data.lens=lens
    targetv=Vector(target); direction=targetv-cam.location; cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler(); scene.camera=cam
    scene.render.filepath=path; bpy.ops.render.render(write_still=True)
    return cam

target=(cx,cy,minz+0.61*h)
camera_render('Camera_3Q',(cx+0.72*h,cy-1.75*h,minz+0.72*h),target,os.path.join(OUT,'frieren_preview_3q.png'),62)
camera_render('Camera_Front',(cx,cy-1.95*h,minz+0.64*h),target,os.path.join(OUT,'frieren_preview_front.png'),62)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'Frieren_realistic_anatomy_rigged.blend'))
print('SUCCESS_OUTPUT',OUT)
