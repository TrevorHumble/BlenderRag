import bpy
import math

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Set render engine to Eevee
bpy.context.scene.render.engine = 'BLENDER_EEVEE'

# Create floor (large plane)
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
floor = bpy.context.active_object
floor.name = "Floor"
floor.scale = (3, 3, 1)
bpy.ops.object.transform_apply(scale=True)

# Create wall 1 (back wall)
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 5, 2))
wall1 = bpy.context.active_object
wall1.name = "Wall_Back"
wall1.scale = (3, 0.1, 3)
bpy.ops.object.transform_apply(scale=True)

# Create wall 2 (side wall)
bpy.ops.mesh.primitive_cube_add(size=2, location=(5, 0, 2))
wall2 = bpy.context.active_object
wall2.name = "Wall_Side"
wall2.scale = (0.1, 3, 3)
bpy.ops.object.transform_apply(scale=True)

# Create window frame (simple plane)
bpy.ops.mesh.primitive_plane_add(size=1.5, location=(2.5, 4.95, 2.5))
window = bpy.context.active_object
window.name = "Window"
window.scale = (1.2, 1, 1)
bpy.ops.object.transform_apply(scale=True)

# Create emissive lamp (small cube)
bpy.ops.mesh.primitive_cube_add(size=0.3, location=(1, 1, 3.5))
lamp = bpy.context.active_object
lamp.name = "Lamp"
bpy.ops.object.transform_apply(scale=True)

# Create sun light for streaming window light
bpy.ops.object.light_add(type='SUN', location=(6, 6, 8))
sun_light = bpy.context.active_object
sun_light.name = "SunLight"
sun_light.data.energy = 1000
sun_light.data.angle = math.radians(5)
sun_light.rotation_euler = (math.radians(45), math.radians(30), 0)

# Create volumetric fog cube (must enclose scene for world volumes)
bpy.ops.mesh.primitive_cube_add(size=120, location=(0, 0, 30))
fog_cube = bpy.context.active_object
fog_cube.name = "VolumetricFog"

# Create materials
# Floor material
floor_mat = bpy.data.materials.new("FloorMat")
floor_mat.use_nodes = True
floor_mat.node_tree.nodes.clear()
floor_nodes = floor_mat.node_tree.nodes
floor_links = floor_mat.node_tree.links

floor_bsdf = floor_nodes.new('ShaderNodeBsdfPrincipled')
floor_bsdf.inputs['Base Color'].default_value = (0.15, 0.15, 0.15, 1.0)
floor_bsdf.inputs['Roughness'].default_value = 0.8

floor_out = floor_nodes.new('ShaderNodeOutputMaterial')
floor_links.new(floor_bsdf.outputs['BSDF'], floor_out.inputs['Surface'])

floor.data.materials.append(floor_mat)

# Wall material
wall_mat = bpy.data.materials.new("WallMat")
wall_mat.use_nodes = True
wall_mat.node_tree.nodes.clear()
wall_nodes = wall_mat.node_tree.nodes
wall_links = wall_mat.node_tree.links

wall_bsdf = wall_nodes.new('ShaderNodeBsdfPrincipled')
wall_bsdf.inputs['Base Color'].default_value = (0.25, 0.24, 0.22, 1.0)
wall_bsdf.inputs['Roughness'].default_value = 0.9

wall_out = wall_nodes.new('ShaderNodeOutputMaterial')
wall_links.new(wall_bsdf.outputs['BSDF'], wall_out.inputs['Surface'])

wall1.data.materials.append(wall_mat)
wall2.data.materials.append(wall_mat)

# Window material (light blue glass-like)
window_mat = bpy.data.materials.new("WindowMat")
window_mat.use_nodes = True
window_mat.node_tree.nodes.clear()
window_nodes = window_mat.node_tree.nodes
window_links = window_mat.node_tree.links

window_bsdf = window_nodes.new('ShaderNodeBsdfPrincipled')
window_bsdf.inputs['Base Color'].default_value = (0.7, 0.85, 1.0, 1.0)
window_bsdf.inputs['Transmission Weight'].default_value = 0.9
window_bsdf.inputs['Roughness'].default_value = 0.1

window_out = window_nodes.new('ShaderNodeOutputMaterial')
window_links.new(window_bsdf.outputs['BSDF'], window_out.inputs['Surface'])

window.data.materials.append(window_mat)

# Emissive lamp material (warm white)
lamp_mat = bpy.data.materials.new("LampMat")
lamp_mat.use_nodes = True
lamp_mat.node_tree.nodes.clear()
lamp_nodes = lamp_mat.node_tree.nodes
lamp_links = lamp_mat.node_tree.links

lamp_emission = lamp_nodes.new('ShaderNodeEmission')
lamp_emission.inputs['Color'].default_value = (1.0, 0.95, 0.85, 1.0)
lamp_emission.inputs['Strength'].default_value = 3.0

lamp_out = lamp_nodes.new('ShaderNodeOutputMaterial')
lamp_links.new(lamp_emission.outputs['Emission'], lamp_out.inputs['Surface'])

lamp.data.materials.append(lamp_mat)

# Volumetric fog material (blue-tinted fog)
fog_mat = bpy.data.materials.new("FogMat")
fog_mat.use_nodes = True
fog_mat.node_tree.nodes.clear()
fog_nodes = fog_mat.node_tree.nodes
fog_links = fog_mat.node_tree.links

fog_volume = fog_nodes.new('ShaderNodeVolumePrincipled')
fog_volume.inputs['Color'].default_value = (0.7, 0.8, 0.95, 1.0)
fog_volume.inputs['Density'].default_value = 0.05

fog_out = fog_nodes.new('ShaderNodeOutputMaterial')
fog_links.new(fog_volume.outputs['Volume'], fog_out.inputs['Volume'])

fog_cube.data.materials.append(fog_mat)

# Hide volumetric cube from viewport
fog_cube.hide_viewport = True

# Configure Eevee volumetrics
scene = bpy.context.scene
scene.eevee.volumetric_start = 0.1
scene.eevee.volumetric_end = 100.0
scene.eevee.volumetric_shadow_samples = 16
scene.eevee.use_volumetric_shadows = False

# Set world background to dark
world = bpy.data.worlds["World"]
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.08, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.5

# Camera setup
bpy.ops.object.camera_add(location=(2, -3, 2))
camera = bpy.context.active_object
camera.name = "Camera"
scene.camera = camera

# Frame rate and render settings
scene.render.fps = 24
scene.render.image_settings.file_format = 'PNG'

print("Moody interior scene created successfully")
