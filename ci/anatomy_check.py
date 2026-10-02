import bpy, os, sys, math, importlib
from mathutils import Vector

ROOT=os.getcwd(); OUT=os.path.join(ROOT,'out'); os.makedirs(OUT,exist_ok=True)

def dynamic_import(suffix,key):
    for name in list(sys.modules):
        if name.endswith(suffix):
            mod=importlib.import_module(name)
            if hasattr(mod,key): return getattr(mod,key)
    raise RuntimeError(f'No module ending {suffix} with {key}')

HumanService=dynamic_import('mpfb.services.humanservice','HumanService')
TargetService=dynamic_import('mpfb.services.targetservice','TargetService')

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

macro=TargetService.get_default_macro_info_dict()
macro['gender']=0.0
macro['age']=0.31
macro['muscle']=0.30
macro['weight']=0.38
macro['height']=0.50
macro['proportions']=0.68
if 'cupsize' in macro: macro['cupsize']=0.34
if 'firmness' in macro: macro['firmness']=0.68
if 'race' in macro:
    macro['race']['caucasian']=0.72; macro['race']['asian']=0.28; macro['race']['african']=0.0

human=HumanService.create_human(mask_helpers=True,detailed_helpers=True,extra_vertex_groups=True,feet_on_ground=True,scale=0.1,macro_detail_dict=macro)
human.name='Frieren_Anatomy_Base'
for p in human.data.polygons: p.use_smooth=True
sub=human.modifiers.new('Anatomy_Subdivision','SUBSURF'); sub.levels=1; sub.render_levels=2
rig=HumanService.add_builtin_rig(human,'default'); rig.name='Frieren_Animation_Rig'

pts=[human.matrix_world @ Vector(c) for c in human.bound_box]
xs=[p.x for p in pts]; ys=[p.y for p in pts]; zs=[p.z for p in pts]
xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys); zmin,zmax=min(zs),max(zs)
h=zmax-zmin; cx=(xmin+xmax)/2; cy=(ymin+ymax)/2
print('FEMALE_BODY_BBOX',xmin,xmax,ymin,ymax,zmin,zmax,'H',h)

def mat(name,color,rough=.5,metal=0.0,sss=0.0):
    m=bpy.data.materials.new(name); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough
    bs.inputs['Metallic'].default_value=metal
    if 'Subsurface Weight' in bs.inputs: bs.inputs['Subsurface Weight'].default_value=sss
    return m
skin=mat('Skin',(0.39,0.20,0.15),.55,sss=.07)
if len(human.data.materials)==0: human.data.materials.append(skin)
else:
    for i in range(len(human.data.materials)): human.data.materials[i]=skin
white=mat('EyeWhite',(0.72,0.72,0.70),.3)
iris=mat('Iris',(0.12,0.34,0.30),.28)
dark=mat('Diagnostic_Shorts',(0.035,0.04,0.05),.65)

head_z=zmin+h*0.895; eye_y=ymin+h*0.075
for sx in (-1,1):
    ex=cx+sx*h*0.031
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,location=(ex,eye_y,head_z),scale=(h*.018,h*.012,h*.0105))
    e=bpy.context.object; e.name=f'Eye_{sx:+d}'; e.data.materials.append(white)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,location=(ex,eye_y-h*.0105,head_z),scale=(h*.0072,h*.003,h*.0072))
    i=bpy.context.object; i.name=f'Iris_{sx:+d}'; i.data.materials.append(iris)

def loft(name,rings,segments,material):
    verts=[]; faces=[]
    for z,rx,ry in rings:
        for j in range(segments):
            a=2*math.pi*j/segments
            verts.append((cx+rx*math.cos(a),cy+ry*math.sin(a),z))
    n=len(rings)
    for k in range(n-1):
        for j in range(segments):
            a=k*segments+j; b=k*segments+(j+1)%segments; c=(k+1)*segments+(j+1)%segments; d=(k+1)*segments+j
            faces.append((a,b,c,d))
    mesh=bpy.data.meshes.new(name+'Mesh'); mesh.from_pydata(verts,[],faces); mesh.update()
    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o); o.data.materials.append(material)
    for p in mesh.polygons: p.use_smooth=True
    sol=o.modifiers.new('Solidify','SOLIDIFY'); sol.thickness=h*.0025
    sub=o.modifiers.new('Smooth','SUBSURF'); sub.levels=1; sub.render_levels=2
    return o
loft('Diagnostic_Shorts',[(zmin+h*.48,h*.105,h*.073),(zmin+h*.535,h*.13,h*.082),(zmin+h*.59,h*.12,h*.075)],72,dark)

bpy.ops.mesh.primitive_plane_add(size=7,location=(0,0,zmin-0.005)); floor=bpy.context.object; floor.data.materials.append(mat('Floor',(0.12,0.13,0.15),.75))

def point_cam(loc,target,lens=58):
    bpy.ops.object.camera_add(location=loc); c=bpy.context.object; c.data.lens=lens
    c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler(); return c
cam=point_cam((h*0.72,ymin-h*1.45,zmin+h*.58),(0,cy,zmin+h*.54),60); bpy.context.scene.camera=cam

def area(name,loc,energy,size,target):
    bpy.ops.object.light_add(type='AREA',location=loc); l=bpy.context.object; l.name=name; l.data.energy=energy; l.data.shape='DISK'; l.data.size=size
    l.rotation_euler=(Vector(target)-l.location).to_track_quat('-Z','Y').to_euler(); return l
focus=(0,cy,zmin+h*.58)
area('Key',(h*.9,ymin-h*.75,zmin+h*1.05),260,2.2,focus)
area('Fill',(-h*.8,ymin-h*.35,zmin+h*.72),110,2.6,focus)
area('Rim',(0,ymax+h*.6,zmin+h*.95),180,1.7,focus)
scene=bpy.context.scene; scene.render.engine='BLENDER_EEVEE_NEXT'; scene.render.resolution_x=720; scene.render.resolution_y=960; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=os.path.join(OUT,'anatomy_check_3q.png')
scene.render.image_settings.color_depth='8'
scene.world.color=(0.015,0.015,0.02)
scene.view_settings.look='AgX - Medium High Contrast'; scene.view_settings.exposure=-0.7
bpy.ops.render.render(write_still=True)
cam.location=(0,ymin-h*1.65,zmin+h*.57); cam.rotation_euler=(Vector((0,cy,zmin+h*.55))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.lens=62
scene.render.filepath=os.path.join(OUT,'anatomy_check_front.png'); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'Frieren_anatomy_base.blend'))
print('ANATOMY_CHECK_OK')
