import bpy
import bmesh
import math
from mathutils import Vector, Euler

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Configure scene
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.view_settings.view_transform = 'AgX'

# Create island base (truncated icosphere for rocky look)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=3.0, location=(0, 0, 0))
base = bpy.context.active_object
base.name = "IslandBase"

# Create grass top
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=2.8, location=(0, 0, 2.8))
grass_top = bpy.context.active_object
grass_top.name = "GrassTop"

# Create rock material (gray, rough)
rock_mat = bpy.data.materials.new(name="RockMaterial")
rock_mat.use_nodes = True
rock_mat.shadow_method = 'HASHED'
bsdf = rock_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.45, 0.42, 0.40, 1.0)
bsdf.inputs["Roughness"].default_value = 0.85

# Create grass material (green)
grass_mat = bpy.data.materials.new(name="GrassMaterial")
grass_mat.use_nodes = True
bsdf_grass = grass_mat.node_tree.nodes["Principled BSDF"]
bsdf_grass.inputs["Base Color"].default_value = (0.2, 0.6, 0.15, 1.0)
bsdf_grass.inputs["Roughness"].default_value = 0.75

# Assign materials
base.data.materials.append(rock_mat)
grass_top.data.materials.append(grass_mat)

# Tree 1 (low-poly cone tree)
bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=1.2, radius2=0.0, depth=3.0, location=(-2.5, -1.5, 3.5))
tree_trunk1 = bpy.context.active_object
tree_trunk1.name = "Tree1Foliage"

tree_mat = bpy.data.materials.new(name="TreeMaterial")
tree_mat.use_nodes = True
bsdf_tree = tree_mat.node_tree.nodes["Principled BSDF"]
bsdf_tree.inputs["Base Color"].default_value = (0.25, 0.5, 0.1, 1.0)
bsdf_tree.inputs["Roughness"].default_value = 0.6
tree_trunk1.data.materials.append(tree_mat)

# Tree 2 (another low-poly cone)
bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=1.0, radius2=0.0, depth=2.5, location=(2.2, 1.8, 3.5))
tree_trunk2 = bpy.context.active_object
tree_trunk2.name = "Tree2Foliage"
tree_trunk2.data.materials.append(tree_mat)

# Add sun lamp for soft daylight
bpy.ops.object.light_add(type='SUN', location=(5.0, 5.0, 10.0))
sun = bpy.context.active_object
sun.name = "Daylight"
sun.data.energy = 2.0
sun.data.angle = 0.05

# Set world background to soft blue
world = scene.world
world.use_nodes = True
bg_node = world.node_tree.nodes["Background"]
bg_node.inputs["Color"].default_value = (0.53, 0.81, 0.92, 1.0)
bg_node.inputs["Strength"].default_value = 1.0

# Adjust camera
camera = bpy.data.objects.get("Camera")
if camera is None:
    bpy.ops.object.camera_add(location=(8.0, 8.0, 6.0))
    camera = bpy.context.active_object
else:
    camera.location = (8.0, 8.0, 6.0)

camera.rotation_euler = Euler((math.radians(60), 0, math.radians(45)), 'XYZ')
scene.camera = camera

# Final render setup
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.samples = 64
