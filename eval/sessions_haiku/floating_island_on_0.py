import bpy
import bmesh
from mathutils import Vector
import random

# ---- Clean slate ----
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# ---- Rocky base (cone-ish island, wider top) ----
bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=2.0, radius2=2.6, depth=3.0, location=(0, 0, 0))
island = bpy.context.active_object
island.name = 'IslandBase'
# Flip so the wide part is on top
island.rotation_euler[0] = 3.14159
bpy.ops.object.transform_apply(rotation=True)

# Subdivide + displace for rocky look
subsurf = island.modifiers.new(name='Subsurf', type='SUBSURF')
subsurf.levels = 2
subsurf.render_levels = 2

disp_tex = bpy.data.textures.new('RockNoise', type='VORONOI')
disp_tex.noise_scale = 0.6
displace = island.modifiers.new(name='Displace', type='DISPLACE')
displace.texture = disp_tex
displace.strength = 0.4

# Rock material
rock_mat = bpy.data.materials.new('RockMat')
rock_mat.use_nodes = True
bsdf = rock_mat.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (0.32, 0.28, 0.24, 1.0)
bsdf.inputs['Roughness'].default_value = 0.9
island.data.materials.append(rock_mat)

# ---- Grass cap on top ----
bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=2.5, depth=0.4, location=(0, 0, 1.5))
grass = bpy.context.active_object
grass.name = 'GrassCap'
grass_mat = bpy.data.materials.new('GrassMat')
grass_mat.use_nodes = True
gbsdf = grass_mat.node_tree.nodes.get('Principled BSDF')
gbsdf.inputs['Base Color'].default_value = (0.18, 0.45, 0.12, 1.0)
gbsdf.inputs['Roughness'].default_value = 0.8
grass.data.materials.append(grass_mat)

# ---- Low-poly trees ----
def make_tree(loc):
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.12, depth=1.0, location=(loc[0], loc[1], loc[2]+0.5))
    trunk = bpy.context.active_object
    trunk.name = 'TreeTrunk'
    trunk_mat = bpy.data.materials.new('TrunkMat')
    trunk_mat.use_nodes = True
    trunk_mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (0.25, 0.15, 0.08, 1.0)
    trunk.data.materials.append(trunk_mat)
    bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.5, radius2=0.0, depth=1.2, location=(loc[0], loc[1], loc[2]+1.5))
    canopy = bpy.context.active_object
    canopy.name = 'TreeCanopy'
    canopy_mat = bpy.data.materials.new('CanopyMat')
    canopy_mat.use_nodes = True
    canopy_mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (0.12, 0.38, 0.10, 1.0)
    canopy.data.materials.append(canopy_mat)

make_tree((0.8, 0.5, 1.7))
make_tree((-0.7, -0.4, 1.7))

# ---- Soft daylight (sun) ----
bpy.ops.object.light_add(type='SUN', location=(4, -4, 8))
sun = bpy.context.active_object
sun.data.energy = 3.0
sun.data.angle = 0.15  # soft shadows
sun.rotation_euler = (0.6, 0.2, 0.8)

# ---- AgX view transform ----
bpy.context.scene.view_settings.view_transform = 'AgX'

# ---- Camera ----
bpy.ops.object.camera_add(location=(7, -7, 5))
cam = bpy.context.active_object
cam.rotation_euler = (1.1, 0.0, 0.785)
bpy.context.scene.camera = cam
