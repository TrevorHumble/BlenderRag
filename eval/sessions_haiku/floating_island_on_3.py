import bpy
import bmesh
import random
from mathutils import Vector

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Set up AgX view transform
scene = bpy.context.scene
scene.display_settings.view_transform = 'AgX'
scene.display_settings.gamma = 1.0

# Create world shader with soft daylight
world = bpy.data.worlds["World"]
world.use_nodes = True
world_nodes = world.node_tree.nodes
world_nodes.clear()

bg_node = world_nodes.new('ShaderNodeBackground')
world_output = world_nodes.new('ShaderNodeOutputWorld')
world_nodes['Background'].inputs[0].default_value = (0.8, 0.9, 1.0, 1.0)
world_nodes['Background'].inputs[1].default_value = 2.0
world.node_tree.links.new(bg_node.outputs[0], world_output.inputs[0])

# Create rocky base island with ico sphere
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=3.0, location=(0, 0, 0))
island_base = bpy.context.active_object
island_base.name = "IslandBase"

# Add displacement modifier for rocky look
island_base.modifiers.new(name="Displace", type='DISPLACE')
disp_mod = island_base.modifiers["Displace"]
disp_mod.strength = 0.6
disp_mod.space = 'LOCAL'

# Add noise texture for displacement
noise_tex = bpy.data.textures.new("IslandNoise", type='CLOUDS')
noise_tex.cloud_type = 'COLOR'
noise_tex.noise_scale = 4.0
disp_mod.texture = noise_tex

# Create grass material
grass_mat = bpy.data.materials.new("Grass")
grass_mat.use_nodes = True
grass_nodes = grass_mat.node_tree.nodes
grass_nodes.clear()

grass_bsdf = grass_nodes.new('ShaderNodeBsdfPrincipled')
mat_output = grass_nodes.new('ShaderNodeOutputMaterial')
grass_nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.2, 0.6, 0.1, 1.0)
grass_nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.7
grass_mat.node_tree.links.new(grass_bsdf.outputs[0], mat_output.inputs[0])

island_base.data.materials.append(grass_mat)

# Create stone material for bottom
stone_mat = bpy.data.materials.new("Stone")
stone_mat.use_nodes = True
stone_nodes = stone_mat.node_tree.nodes
stone_nodes.clear()

stone_bsdf = stone_nodes.new('ShaderNodeBsdfPrincipled')
stone_out = stone_nodes.new('ShaderNodeOutputMaterial')
stone_nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.35, 0.35, 0.35, 1.0)
stone_nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.8
stone_mat.node_tree.links.new(stone_bsdf.outputs[0], stone_out.inputs[0])

# Add second material slot to island
island_base.data.materials.append(stone_mat)

# Create first low-poly tree
def create_lowpoly_tree(location, scale=1.0):
    # Tree trunk - simple cylinder using ico sphere scaled
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.2 * scale, location=location)
    trunk = bpy.context.active_object
    trunk.scale = (1, 1, 2.5)
    trunk.name = f"TreeTrunk_{location[0]}"

    # Apply scale
    bpy.context.view_layer.objects.active = trunk
    bpy.ops.object.transform_apply(scale=True)

    # Trunk material - brown
    trunk_mat = bpy.data.materials.new(f"TreeBark_{location[0]}")
    trunk_mat.use_nodes = True
    trunk_nodes = trunk_mat.node_tree.nodes
    trunk_nodes.clear()
    trunk_bsdf = trunk_nodes.new('ShaderNodeBsdfPrincipled')
    trunk_out = trunk_nodes.new('ShaderNodeOutputMaterial')
    trunk_nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.4, 0.25, 0.1, 1.0)
    trunk_nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.8
    trunk_mat.node_tree.links.new(trunk_bsdf.outputs[0], trunk_out.inputs[0])
    trunk.data.materials.append(trunk_mat)

    # Tree canopy - simple icosphere at top
    canopy_height = location[2] + 2.0 * scale
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.2 * scale, location=(location[0], location[1], canopy_height))
    canopy = bpy.context.active_object
    canopy.name = f"TreeCanopy_{location[0]}"

    # Canopy material - green
    canopy_mat = bpy.data.materials.new(f"TreeLeaves_{location[0]}")
    canopy_mat.use_nodes = True
    canopy_nodes = canopy_mat.node_tree.nodes
    canopy_nodes.clear()
    canopy_bsdf = canopy_nodes.new('ShaderNodeBsdfPrincipled')
    canopy_out = canopy_nodes.new('ShaderNodeOutputMaterial')
    canopy_nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.1, 0.5, 0.05, 1.0)
    canopy_nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.6
    canopy_mat.node_tree.links.new(canopy_bsdf.outputs[0], canopy_out.inputs[0])
    canopy.data.materials.append(canopy_mat)

    return trunk, canopy

# Create two trees at opposite edges
tree1_trunk, tree1_canopy = create_lowpoly_tree((-2.0, -1.5, 3.2), scale=0.8)
tree2_trunk, tree2_canopy = create_lowpoly_tree((1.8, 2.0, 3.2), scale=0.9)

# Add sun light for soft daylight
bpy.ops.object.light_add(type='SUN', location=(5, 5, 8))
sun = bpy.context.active_object
sun.name = "SunLight"
sun.data.energy = 1500
sun.data.angle = 0.5

# Join tree trunks and canopies to themselves for cleaner hierarchy
bpy.context.view_layer.objects.active = tree1_trunk
tree1_trunk.select_set(True)
tree1_canopy.select_set(True)
bpy.ops.object.join()

bpy.context.view_layer.objects.active = tree2_trunk
tree2_trunk.select_set(True)
tree2_canopy.select_set(True)
bpy.ops.object.join()

# Set viewport shading to solid/material preview
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'

# Camera setup
bpy.ops.object.camera_add(location=(8, -6, 5))
camera = bpy.context.active_object
camera.name = "Camera"
scene.camera = camera
camera.rotation_euler = (1.2, 0, 0.785)

# Render settings for Eevee
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.use_taa_reprojection = True
scene.eevee.taa_render_samples = 32

print("Floating island scene created successfully with AgX view transform!")
