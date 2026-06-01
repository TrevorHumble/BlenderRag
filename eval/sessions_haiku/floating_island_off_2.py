import bpy
import bmesh
from mathutils import Vector, Matrix
import math

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False, confirm=False)

# ===== ROCKY BASE =====
bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, -1.5), scale=2)
base = bpy.context.active_object
base.name = "RockyBase"

# Add some roughness with a subdivision surface modifier
bpy.ops.object.modifier_add(type='SUBDIVISION_SURFACE')
base.modifiers["Subdivision"].levels = 2
base.modifiers["Subdivision"].render_levels = 3

# Add displace for rocky look
bpy.ops.object.modifier_add(type='DISPLACE')
disp_mod = base.modifiers["Displace"]
disp_mod.strength = 0.4

# Enter edit mode and add random scaling for rocky appearance
bpy.context.view_layer.objects.active = base
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.noise(scale=0.5)
bpy.ops.object.mode_set(mode='OBJECT')

# Create rocky material (dark gray stone)
rock_mat = bpy.data.materials.new(name="RockMaterial")
rock_mat.use_nodes = True
bsdf = rock_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs[0].default_value = (0.3, 0.28, 0.25, 1.0)  # Brownish gray
bsdf.inputs[9].default_value = 0.6  # Roughness
base.data.materials.append(rock_mat)

# ===== GRASS ISLAND TOP =====
bpy.ops.mesh.primitive_plane_add(location=(0, 0, 0.8), scale=2)
grass_plane = bpy.context.active_object
grass_plane.name = "GrassTop"
grass_plane.scale.z = 0.2

# Subdivide for detail
bpy.context.view_layer.objects.active = grass_plane
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.subdivide(number_cuts=4)
bpy.ops.object.mode_set(mode='OBJECT')

# Add slight noise for terrain variation
bpy.ops.object.modifier_add(type='DISPLACE')
grass_plane.modifiers["Displace"].strength = 0.15

# Grass material (green)
grass_mat = bpy.data.materials.new(name="GrassMaterial")
grass_mat.use_nodes = True
bsdf = grass_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs[0].default_value = (0.1, 0.5, 0.1, 1.0)  # Green
bsdf.inputs[9].default_value = 0.8  # Roughness
grass_plane.data.materials.append(grass_mat)

# ===== LOW-POLY TREE 1 =====
# Trunk
bpy.ops.mesh.primitive_cylinder_add(location=(-1.2, 0.8, 1.5), scale=0.15)
trunk1 = bpy.context.active_object
trunk1.scale.z = 1.2
trunk1.name = "Trunk1"

# Foliage (cone)
bpy.ops.mesh.primitive_cone_add(vertices=8, location=(-1.2, 0.8, 2.5), scale=0.6)
foliage1 = bpy.context.active_object
foliage1.name = "Foliage1"

# Create tree material (brown trunk, green foliage)
trunk_mat = bpy.data.materials.new(name="TrunkMaterial")
trunk_mat.use_nodes = True
bsdf = trunk_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs[0].default_value = (0.4, 0.25, 0.1, 1.0)  # Brown
trunk1.data.materials.append(trunk_mat)

foliage_mat = bpy.data.materials.new(name="FoliageMaterial")
foliage_mat.use_nodes = True
bsdf = foliage_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs[0].default_value = (0.2, 0.6, 0.2, 1.0)  # Forest green
bsdf.inputs[9].default_value = 0.7
foliage1.data.materials.append(foliage_mat)

# ===== LOW-POLY TREE 2 =====
# Trunk
bpy.ops.mesh.primitive_cylinder_add(location=(1.0, -0.6, 1.5), scale=0.12)
trunk2 = bpy.context.active_object
trunk2.scale.z = 1.3
trunk2.name = "Trunk2"
trunk2.data.materials.append(trunk_mat)

# Foliage (sphere)
bpy.ops.mesh.primitive_uv_sphere_add(vertices=8, rings=6, location=(1.0, -0.6, 2.6), scale=0.5)
foliage2 = bpy.context.active_object
foliage2.name = "Foliage2"
foliage2.data.materials.append(foliage_mat)

# ===== LIGHTING =====
# Sun light for soft daylight
bpy.ops.object.light_add(type='SUN', location=(5, 5, 5))
sun = bpy.context.active_object
sun.name = "SunLight"
sun.data.energy = 2.0
sun.data.angle = math.radians(5)

# Soft fill light
bpy.ops.object.light_add(type='AREA', location=(-3, -3, 3))
fill_light = bpy.context.active_object
fill_light.name = "FillLight"
fill_light.data.energy = 0.5
fill_light.data.size = 3

# ===== SCENE & RENDERING SETUP =====
scene = bpy.context.scene

# Set render engine to Eevee
scene.render.engine = 'BLENDER_EEVEE_NEXT'

# World background
world = scene.world
world.use_nodes = True
bg_node = world.node_tree.nodes["Background"]
bg_node.inputs[0].default_value = (0.7, 0.8, 0.95, 1.0)  # Sky blue
bg_node.inputs[1].default_value = 1.0  # Strength

# AgX view transform (case-sensitive in 5.1)
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'Medium High Contrast'
scene.view_settings.exposure = 0.0

# Camera setup
bpy.ops.object.camera_add(location=(3, -3, 2.5))
camera = bpy.context.active_object
camera.name = "Camera"
camera.rotation_euler = (math.radians(75), 0, math.radians(45))
scene.camera = camera

# Render settings
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.samples = 32

print("Floating island scene created successfully!")
