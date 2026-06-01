import bpy
import bmesh
from mathutils import Vector, Matrix

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False, confirm=False)

# Create rocky base using icosphere
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=3.0, location=(0, 0, 0))
base = bpy.context.active_object
base.name = "RockyBase"

# Add subdiv modifier for detail
subdiv = base.modifiers.new(name="Subdiv", type='SUBDIVISION_SURFACE')
subdiv.levels = 2
subdiv.render_levels = 3

# Create rocky material (brown/gray)
rock_mat = bpy.data.materials.new(name="RockMaterial")
rock_mat.use_nodes = True
rock_mat.node_tree.nodes.clear()

# Add nodes for rock material
nodes = rock_mat.node_tree.nodes
links = rock_mat.node_tree.links
principled = nodes.new(type='ShaderNodeBsdfPrincipled')
output = nodes.new(type='ShaderNodeOutputMaterial')

# Set rock color and roughness
principled.inputs['Base Color'].default_value = (0.35, 0.32, 0.30, 1.0)
principled.inputs['Roughness'].default_value = 0.8

links.new(principled.outputs['BSDF'], output.inputs['Surface'])
base.data.materials.append(rock_mat)

# Create grass surface on top
bpy.ops.mesh.primitive_uv_sphere_add(radius=3.2, location=(0, 0, 2.0))
grass_base = bpy.context.active_object
grass_base.name = "GrassTop"

# Scale down Z to flatten it
grass_base.scale = (1.0, 1.0, 0.5)
bpy.ops.object.transform_apply(scale=True)

# Grass material (green)
grass_mat = bpy.data.materials.new(name="GrassMaterial")
grass_mat.use_nodes = True
grass_mat.node_tree.nodes.clear()

nodes = grass_mat.node_tree.nodes
links = grass_mat.node_tree.links
grass_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
grass_output = nodes.new(type='ShaderNodeOutputMaterial')

grass_principled.inputs['Base Color'].default_value = (0.2, 0.5, 0.15, 1.0)
grass_principled.inputs['Roughness'].default_value = 0.6

links.new(grass_principled.outputs['BSDF'], grass_output.inputs['Surface'])
grass_base.data.materials.append(grass_mat)

# Create first simple low-poly tree
bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.3, depth=2.0, location=(2.0, 1.5, 3.2))
tree1_trunk = bpy.context.active_object
tree1_trunk.name = "Tree1_Trunk"

# Create foliage for tree 1 (cone)
bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=1.2, depth=2.5, location=(2.0, 1.5, 5.0))
tree1_foliage = bpy.context.active_object
tree1_foliage.name = "Tree1_Foliage"

# Tree 2 - another cone structure
bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.25, depth=1.8, location=(-2.5, 1.0, 3.2))
tree2_trunk = bpy.context.active_object
tree2_trunk.name = "Tree2_Trunk"

bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=1.0, depth=2.0, location=(-2.5, 1.0, 4.8))
tree2_foliage = bpy.context.active_object
tree2_foliage.name = "Tree2_Foliage"

# Wood material for trunks
wood_mat = bpy.data.materials.new(name="WoodMaterial")
wood_mat.use_nodes = True
wood_mat.node_tree.nodes.clear()

nodes = wood_mat.node_tree.nodes
links = wood_mat.node_tree.links
wood_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
wood_output = nodes.new(type='ShaderNodeOutputMaterial')

wood_principled.inputs['Base Color'].default_value = (0.4, 0.25, 0.1, 1.0)
wood_principled.inputs['Roughness'].default_value = 0.7

links.new(wood_principled.outputs['BSDF'], wood_output.inputs['Surface'])

# Foliage material (dark green)
foliage_mat = bpy.data.materials.new(name="FoliageMaterial")
foliage_mat.use_nodes = True
foliage_mat.node_tree.nodes.clear()

nodes = foliage_mat.node_tree.nodes
links = foliage_mat.node_tree.links
foliage_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
foliage_output = nodes.new(type='ShaderNodeOutputMaterial')

foliage_principled.inputs['Base Color'].default_value = (0.15, 0.35, 0.1, 1.0)
foliage_principled.inputs['Roughness'].default_value = 0.5

links.new(foliage_principled.outputs['BSDF'], foliage_output.inputs['Surface'])

# Assign materials to tree parts
tree1_trunk.data.materials.append(wood_mat)
tree1_foliage.data.materials.append(foliage_mat)
tree2_trunk.data.materials.append(wood_mat)
tree2_foliage.data.materials.append(foliage_mat)

# Setup world lighting with simple sky
world = bpy.data.worlds["World"]
world.use_nodes = True
world.node_tree.nodes.clear()

world_nodes = world.node_tree.nodes
world_links = world.node_tree.links

# Add background shader with sky-like color
bg_node = world_nodes.new(type='ShaderNodeBackground')
world_output = world_nodes.new(type='ShaderNodeOutputWorld')

# Set light blue sky color
bg_node.inputs['Color'].default_value = (0.5, 0.7, 0.9, 1.0)
bg_node.inputs['Strength'].default_value = 1.5

world_links.new(bg_node.outputs['Background'], world_output.inputs['Surface'])

# Set view transform to AgX (case-sensitive in Blender 5.1)
scene = bpy.context.scene
scene.display_settings.display_device = 'None'

# Try to set view transform (check available transforms)
try:
    scene.view_settings.view_transform = 'AgX'
except:
    scene.view_settings.view_transform = 'Filmic'

# Add a simple directional light for daylight
bpy.ops.object.light_add(type='SUN', location=(5.0, 5.0, 8.0))
sun = bpy.context.active_object
sun.name = "Daylight_Sun"
sun.data.energy = 2.0
sun.data.angle = 0.05

# Set render engine to Eevee for fast preview
scene.render.engine = 'BLENDER_EEVEE_NEXT'

# Optional: set camera view
bpy.ops.object.camera_add(location=(8.0, 8.0, 6.0))
camera = bpy.context.active_object
camera.name = "Camera"

# Point camera at origin
direction = Vector((0, 0, 0)) - camera.location
rot_quat = direction.to_track_quat('-Z', 'Y')
camera.rotation_euler = rot_quat.to_euler()

scene.camera = camera
