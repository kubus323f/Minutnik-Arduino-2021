import bpy
import math
import os
import runpy
from mathutils import Vector

ROOT=os.getcwd(); OUT=os.path.join(ROOT,'out')
ns=runpy.run_path(os.path.join(ROOT,'ci','build_frieren_v3.py'),run_name='frieren_v3_base')

h=ns['h']; zmin=ns['zmin']; ymin=ns['ymin']; ymax=ns['ymax']; cy=ns['cy']; rig=ns['rig']; human=ns['human']
white=ns['white']; gold=ns['gold']; black=ns['black']; hairmat=ns['hairmat']; hairhi=ns['hairhi']; skin=ns['skin']
loft=ns['loft']; sweep=ns['sweep']; ribbon=ns['ribbon']; cube=ns['cube']; world_bone_points=ns['world_bone_points']; parent_to_bone=ns['parent_to_bone']

# Restore intended world placement. V3 used bone parenting without preserving world transforms.
# Geometry built directly in world coordinates should remain unparented for validation;
# final animation parenting is added only after visual renders.
world_prefixes=(
    'Hair_Scalp','Bang_','Tail_','HairTie_','FrontLock_','Elf_Ear_',
    'Eye_','Iris_','Pupil_','Earring_','Gold_Collar','Collar_Gem','Shoulder_Gem_',
    'Dress','Gold_Hem','Capelet','Chest_Panel','Panel_Gold_Edge_'
)
for obj in list(bpy.data.objects):
    if obj.name.startswith(world_prefixes):
        obj.parent=None
        obj.parent_bone=''
        obj.parent_type='OBJECT'

# The fitted dress in V3 intentionally began below the clavicles. Add the actual
# high-neck inner robe so the chest/shoulder region is anatomically covered.
bodice=loft('Upper_Robe',[
    (zmin+h*.605,h*.132,h*.093,0.0),
    (zmin+h*.675,h*.148,h*.100,0.0),
    (zmin+h*.735,h*.163,h*.108,0.0),
    (zmin+h*.775,h*.125,h*.083,0.0),
    (zmin+h*.803,h*.050,h*.039,0.0),
],104,white,pleats=0,subdiv=2,solidify=h*.0020)

# Refined collar ring outside upper robe.
bpy.ops.mesh.primitive_torus_add(major_radius=h*.047,minor_radius=h*.0065,major_segments=72,minor_segments=16,location=(0,cy-h*.001,zmin+h*.802))
collar2=bpy.context.object; collar2.name='Gold_Collar_V4'; collar2.scale=(1.0,.80,1.0); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); collar2.data.materials.append(gold)
for p in collar2.data.polygons: p.use_smooth=True

# Hide/remove the exposed-skinned V3 leggings and rebuild slightly outside the anatomical legs.
for name in ['Legging_L','Legging_R']:
    o=bpy.data.objects.get(name)
    if o: bpy.data.objects.remove(o,do_unlink=True)
for side in ('L','R'):
    legpts=world_bone_points(rig,[f'upperleg01.{side}',f'upperleg02.{side}',f'lowerleg01.{side}',f'lowerleg02.{side}',f'foot.{side}'])
    if len(legpts)<4:
        sx=-1 if side=='L' else 1
        legpts=[Vector((sx*h*.07,0,zmin+h*.50)),Vector((sx*h*.075,0,zmin+h*.32)),Vector((sx*h*.065,0,zmin+h*.12)),Vector((sx*h*.065,-h*.03,zmin+h*.04))]
    n=len(legpts); radii=[]
    for i in range(n):
        t=i/(n-1)
        r=h*(.061*(1-t)+.031*t)
        radii.append((r,r*.86))
    sweep('LeggingV4_'+side,legpts,radii,black,40,2)

# Eyes are now back at the face. Make them slightly larger vertically/horizontally,
# retaining realistic depth so the eyelids still overlap the globes.
for side in ('L','R'):
    e=bpy.data.objects.get('Eye_'+side)
    if e:
        e.scale.x*=1.10; e.scale.z*=1.08
    ir=bpy.data.objects.get('Iris_'+side)
    pu=bpy.data.objects.get('Pupil_'+side)
    if ir:
        ir.scale.x*=1.06; ir.scale.y*=1.06; ir.scale.z*=1.06
    if pu:
        pu.scale.x*=1.06; pu.scale.y*=1.06; pu.scale.z*=1.06

# Brows and subtle upper lashes. The front axis is -Y.
eyeL=bpy.data.objects.get('Eye_L'); eyeR=bpy.data.objects.get('Eye_R')
for side,e in [('L',eyeL),('R',eyeR)]:
    if not e: continue
    sx=-1 if side=='L' else 1
    x=e.location.x; y=e.location.y-h*.014; z=e.location.z
    brow_pts=[(x-sx*h*.020,y,z+h*.030),(x,y-h*.001,z+h*.034),(x+sx*h*.021,y,z+h*.029)]
    ribbon('Brow_'+side,brow_pts,[h*.0045,h*.0055,h*.0025],hairmat,h*.0012)
    lash_pts=[(x-sx*h*.018,y-h*.001,z+h*.006),(x,y-h*.002,z+h*.010),(x+sx*h*.019,y-h*.001,z+h*.006)]
    ribbon('UpperLash_'+side,lash_pts,[h*.0024,h*.0030,h*.0015],black,h*.0008)

# Add shorter layered hair cards around cheeks so the scalp cap does not read as a helmet.
for side,sx in [('L',-1),('R',1)]:
    for k in range(4):
        root=(sx*h*(.025+.014*k),cy-h*(.045-.006*k),zmin+h*(.970-.008*k))
        mid=(sx*h*(.050+.012*k),cy-h*(.058-.004*k),zmin+h*(.900-.012*k))
        tip=(sx*h*(.062+.014*k),cy-h*(.042-.003*k),zmin+h*(.810-.018*k))
        ribbon(f'CheekHair_{side}_{k}',[root,mid,tip],[h*.022,h*.028,h*.005],hairhi if k%2 else hairmat,h*.0012)

# Refine cape by moving its upper edge downward slightly and narrowing shoulders.
for nm in ['Capelet','Capelet_Gold_Trim']:
    o=bpy.data.objects.get(nm)
    if o:
        # local world-coordinate mesh: modest X/Y contraction keeps it draped, not wing-like
        for v in o.data.vertices:
            v.co.x*=0.91
            v.co.y*=0.93
            if v.co.z>zmin+h*.755:
                v.co.z-=h*.018

# Lower the front panel into the robe instead of floating above it.
for o in list(bpy.data.objects):
    if o.name.startswith(('Chest_Panel','Chest_Stripe_','Panel_Gold_Edge_')):
        o.location.y += h*.018

# Lighting/camera reused from v3, but render only V4 outputs.
scene=bpy.context.scene
scene.render.resolution_x=900; scene.render.resolution_y=1200
cam=scene.camera
cam.location=(h*.58,ymin-h*1.42,zmin+h*.60); cam.data.lens=62
ns['aim'](cam,(0,cy,zmin+h*.57))
scene.render.filepath=os.path.join(OUT,'frieren_v4_3q.png')
bpy.ops.render.render(write_still=True)

cam.location=(0,ymin-h*1.58,zmin+h*.60); cam.data.lens=64; ns['aim'](cam,(0,cy,zmin+h*.57))
scene.render.filepath=os.path.join(OUT,'frieren_v4_front.png')
bpy.ops.render.render(write_still=True)

cam.location=(h*.20,ymin-h*.63,zmin+h*.875); cam.data.lens=82; ns['aim'](cam,(0,cy-h*.012,zmin+h*.865))
scene.render.resolution_x=1000; scene.render.resolution_y=1000
scene.render.filepath=os.path.join(OUT,'frieren_v4_face.png')
bpy.ops.render.render(write_still=True)

# After visual state is captured, establish animation relationships while preserving transforms.
def bone_parent_preserve(obj,bone='head'):
    if not rig.data.bones.get(bone): return
    mw=obj.matrix_world.copy()
    obj.parent=rig; obj.parent_type='BONE'; obj.parent_bone=bone
    obj.matrix_world=mw

for o in list(bpy.data.objects):
    if o.name.startswith(('Hair_Scalp','Bang_','Tail_','HairTie_','FrontLock_','CheekHair_','Elf_Ear_','Eye_','Iris_','Pupil_','Earring_','Brow_','UpperLash_','Gold_Collar','Collar_Gem')):
        bone_parent_preserve(o,'head')

# Bind garments only after renders, so weighting cannot distort the visual QA result.
for o in [bodice]:
    ns['bind_auto'](o,rig)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'Frieren_v4_animation_ready.blend'))
print('FRIEREN_V4_OK')
