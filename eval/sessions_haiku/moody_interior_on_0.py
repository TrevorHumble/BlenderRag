import bpy
import math
from mathutils import Vector

# Clear default objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# ==================== GEOMETRY ====================

# Floor - large plane
bpy.ops.mesh.primitive_plane_add(size=10.0, location=(0, 0, 0))
floor = bpy.context.active_object
floor.name = "Floor"
floor.scale = (5, 5, 1)
bpy.ops.object.transform_apply(scale=True)

# Wall 1 (back wall)
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 5, 2.5))
wall1 = bpy.context.active_object
wall1.name = "Wall_Back"
wall1.scale = (5, 0.2, 5)
bpy.ops.object.transform_apply(scale=True)

# Wall 2 (left wall)
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-5, 0, 2.5))
wall2 = bpy.context.active_object
wall2.name = "Wall_Left"
wall2.scale = (0.2, 5, 5)
bpy.ops.object.transform_apply(scale=True)

# Window frame (cube with simple opening)
bpy.ops.mesh.primitive_cube_add(size=2.0, location=(3, 5, 2.5))
window = bpy.context.active_object
window.name = "Window"
window.scale = (1.5, 0.15, 2.0)
bpy.ops.object.transform_apply(scale=True)

# ==================== MATERIALS ====================

# Floor material - dark matte
floor_mat = bpy.data.materials.new(name="FloorMaterial")
floor_mat.use_nodes = True
floor_mat.node_tree.nodes.clear()
links = floor_mat.node_tree.links

floor_bsdf = floor_mat.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
floor_bsdf.inputs['Base Color'].default_value = (0.1, 0.1, 0.1, 1.0)
floor_bsdf.inputs['Roughness'].default_value = 0.8

floor_output = floor_mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
links.new(floor_bsdf.outputs['BSDF'], floor_output.inputs['Surface'])

floor.data.materials.append(floor_mat)

# Wall materials - warm grey
wall_mat = bpy.data.materials.new(name="WallMaterial")
wall_mat.use_nodes = True
wall_mat.node_tree.nodes.clear()
links = wall_mat.node_tree.links

wall_bsdf = wall_mat.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
wall_bsdf.inputs['Base Color'].default_value = (0.25, 0.22, 0.20, 1.0)
wall_bsdf.inputs['Roughness'].default_value = 0.7

wall_output = wall_mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
links.new(wall_bsdf.outputs['BSDF'], wall_output.inputs['Surface'])

wall1.data.materials.append(wall_mat)
wall2.data.materials.append(wall_mat)

# Window material - cool glass with slight transmissivity
window_mat = bpy.data.materials.new(name="WindowMaterial")
window_mat.use_nodes = True
window_mat.node_tree.nodes.clear()
links = window_mat.node_tree.links

window_bsdf = window_mat.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
window_bsdf.inputs['Base Color'].default_value = (0.7, 0.85, 0.95, 1.0)
window_bsdf.inputs['Transmission'].default_value = 0.5
window_bsdf.inputs['Roughness'].default_value = 0.1

window_output = window_mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
links.new(window_bsdf.outputs['BSDF'], window_output.inputs['Surface'])

window.data.materials.append(window_mat)

# ==================== LIGHTING ====================

# Sunlight from window
bpy.ops.object.light_add(type='SUN', location=(5, 5, 4))
sun = bpy.context.active_object
sun.name = "SunLight"
sun.data.energy = 1.5
sun.data.color = (1.0, 0.95, 0.85)
sun.rotation_euler = (math.radians(45), math.radians(30), 0)

# Emissive lamp in corner
bpy.ops.object.light_add(type='POINT', location=(-3, -3, 2.5), radius=0.2)
lamp = bpy.context.active_object
lamp.name = "EmissiveLamp"
lamp.data.energy = 2.0
lamp.data.color = (1.0, 0.8, 0.5)

# Create emissive material for lamp object (small sphere)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(-3, -3, 2.5))
lamp_sphere = bpy.context.active_object
lamp_sphere.name = "LampSphere"

lamp_emissive = bpy.data.materials.new(name="LampEmissive")
lamp_emissive.use_nodes = True
lamp_emissive.node_tree.nodes.clear()
links = lamp_emissive.node_tree.links

emit_node = lamp_emissive.node_tree.nodes.new(type='ShaderNodeEmission')
emit_node.inputs['Color'].default_value = (1.0, 0.8, 0.5, 1.0)
emit_node.inputs['Strength'].default_value = 3.0

emit_output = lamp_emissive.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
links.new(emit_node.outputs['Emission'], emit_output.inputs['Surface'])

lamp_sphere.data.materials.append(lamp_emissive)

# ==================== WORLD & VOLUMETRICS ====================

# Set world background to dark
world = bpy.data.worlds["World"]
world.use_nodes = True
world.node_tree.nodes.clear()
links = world.node_tree.links

world_bg = world.node_tree.nodes.new(type='ShaderNodeBackground')
world_bg.inputs['Color'].default_value = (0.05, 0.05, 0.08, 1.0)
world_bg.inputs['Strength'].default_value = 0.5

# Add volume scatter for atmospheric effect
world_vol = world.node_tree.nodes.new(type='ShaderNodeVolumeScatter')
world_vol.inputs['Color'].default_value = (0.9, 0.9, 1.0, 1.0)
world_vol.inputs['Density'].default_value = 0.05

world_output = world.node_tree.nodes.new(type='ShaderNodeOutputWorld')
links.new(world_bg.outputs['Background'], world_output.inputs['Surface'])
links.new(world_vol.outputs['Volume'], world_output.inputs['Volume'])

# ==================== RENDER SETTINGS ====================

# Set render engine to EEVEE
scene = bpy.context.scene
scene.render.engine = 'EEVEE_NEXT'

# Enable volumetrics in EEVEE
eevee = scene.eevee
eevee.use_volumetric_shadows = True
eevee.volumetric_tile_size = '8x8'
eevee.volumetric_samples = 64
eevee.volumetric_ray_depth = 8

# Bloom for emissive effect
eevee.use_bloom = True
eevee.bloom_intensity = 0.5
eevee.bloom_threshold = 0.8

# Camera setup
bpy.ops.object.camera_add(location=(2, -3, 1.5))
camera = bpy.context.active_object
camera.rotation_euler = (math.radians(15), 0, math.radians(45))
scene.camera = camera

# ==================== FINAL SETUP ====================

# Set viewport shading to rendered
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'

print("Moody interior scene created successfully!")
