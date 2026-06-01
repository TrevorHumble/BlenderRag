import bpy
import bmesh
from mathutils import Vector
import random

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create rocky base using displacement on a UV sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=2, location=(0, 0, 0))
base = bpy.context.active_object
base.name = "IslandBase"

# Add subdivision surface modifier to smooth the base
subdiv = base.modifiers.new(name="Subdivision", type='SUBSURF')
subdiv.levels = 2
subdiv.render_levels = 3

# Add displacement modifier for rocky look
disp = base.modifiers.new(name="Displacement", type='DISPLACE')
disp.strength = 0.8

# Create a simple noise texture for displacement
noise_texture = bpy.data.textures.new("RockNoise", type='CLOUDS')
disp.texture = noise_texture

# Create material for rocky base
rock_mat = bpy.data.materials.new(name="RockMaterial")
rock_mat.use_nodes = True
bsdf = rock_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs['Base Color'].default_value = (0.4, 0.35, 0.3, 1.0)
bsdf.inputs['Roughness'].default_value = 0.8

base.data.materials.append(rock_mat)

# Create grass plane on top
bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, 2.2))
grass_top = bpy.context.active_object
grass_top.name = "GrassTop"

# Add material for grass
grass_mat = bpy.data.materials.new(name="GrassMaterial")
grass_mat.use_nodes = True
grass_bsdf = grass_mat.node_tree.nodes["Principled BSDF"]
grass_bsdf.inputs['Base Color'].default_value = (0.2, 0.6, 0.15, 1.0)
grass_bsdf.inputs['Roughness'].default_value = 0.6

grass_top.data.materials.append(grass_mat)

# Create first low-poly tree
def create_lowpoly_tree(x, y, name_prefix):
    # Tree trunk - simple cylinder
    bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=1.5, location=(x, y, 2.8))
    trunk = bpy.context.active_object
    trunk.name = f"{name_prefix}_Trunk"

    # Trunk material
    trunk_mat = bpy.data.materials.new(name=f"{name_prefix}_TrunkMat")
    trunk_mat.use_nodes = True
    trunk_bsdf = trunk_mat.node_tree.nodes["Principled BSDF"]
    trunk_bsdf.inputs['Base Color'].default_value = (0.4, 0.25, 0.1, 1.0)
    trunk.data.materials.append(trunk_mat)

    # Tree foliage - cone (low-poly style)
    bpy.ops.mesh.primitive_cone_add(radius1=0.8, depth=1.5, vertices=6, location=(x, y, 3.5))
    foliage = bpy.context.active_object
    foliage.name = f"{name_prefix}_Foliage"

    # Foliage material - leafy green
    foliage_mat = bpy.data.materials.new(name=f"{name_prefix}_FoliageMat")
    foliage_mat.use_nodes = True
    foliage_bsdf = foliage_mat.node_tree.nodes["Principled BSDF"]
    foliage_bsdf.inputs['Base Color'].default_value = (0.1, 0.5, 0.05, 1.0)
    foliage_bsdf.inputs['Roughness'].default_value = 0.7
    foliage.data.materials.append(foliage_mat)

# Create two trees
create_lowpoly_tree(-1.2, -0.8, "Tree1")
create_lowpoly_tree(1.0, 0.6, "Tree2")

# Set up world lighting
world = bpy.data.worlds["World"]
world.use_nodes = True
world_nodes = world.node_tree.nodes
world_links = world.node_tree.links

# Clear default nodes
world_nodes.clear()

# Add background light with soft daylight color
world_bg = world_nodes.new(type='ShaderNodeBackground')
world_bg.inputs['Color'].default_value = (0.9, 0.95, 1.0, 1.0)
world_bg.inputs['Strength'].default_value = 1.5

world_output = world_nodes.new(type='ShaderNodeOutputWorld')
world_links.new(world_bg.outputs['Background'], world_output.inputs['Surface'])

# Add sun light for directional daylight
bpy.ops.object.light_add(type='SUN', location=(5, 5, 8))
sun = bpy.context.active_object
sun.name = "Daylight"
sun.data.energy = 2.5
sun.data.angle = 0.05

# Set render engine to Eevee Next and configure
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'

# Set view transform to AgX
scene.display_settings.view_transform = 'AgX'

# Set render resolution
scene.render.resolution_x = 1280
scene.render.resolution_y = 720

# Set camera
bpy.ops.object.camera_add(location=(5, -5, 4))
camera = bpy.context.active_object
camera.name = "Camera"
scene.camera = camera

# Point camera at island center
direction = Vector((0, 0, 0)) - camera.location
rot_quat = direction.to_track_quat('-Z', 'Y')
camera.rotation_euler = rot_quat.to_euler()

# Frame the scene nicely
camera.data.lens = 50

print("Floating island scene created successfully!")
