import bpy
import math

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Set render engine to Eevee
bpy.context.scene.render.engine = 'BLENDER_EEVEE'

# Add floor plane
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
floor = bpy.context.active_object
floor.name = "Floor"

# Add first wall (back)
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 5, 5), rotation=(math.pi/2, 0, 0))
wall1 = bpy.context.active_object
wall1.name = "WallBack"

# Add second wall (right side)
bpy.ops.mesh.primitive_plane_add(size=10, location=(5, 0, 5), rotation=(math.pi/2, 0, math.pi/2))
wall2 = bpy.context.active_object
wall2.name = "WallRight"

# Add window plane (in wall1 as a portal to exterior light)
bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 4.9, 6), rotation=(math.pi/2, 0, 0))
window = bpy.context.active_object
window.name = "Window"

# Add emissive lamp (area light)
bpy.ops.object.light_add(type='AREA', radius=0.5, location=(2, 2, 3))
lamp = bpy.context.active_object
lamp.data.energy = 150
lamp.data.size = 1.5
lamp.name = "EmissiveLamp"

# Create material for floor (matte dark surface)
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

# Create material for walls (warm dark gray)
wall_mat = bpy.data.materials.new("WallMat")
wall_mat.use_nodes = True
wall_mat.node_tree.nodes.clear()
wall_nodes = wall_mat.node_tree.nodes
wall_links = wall_mat.node_tree.links

wall_bsdf = wall_nodes.new('ShaderNodeBsdfPrincipled')
wall_bsdf.inputs['Base Color'].default_value = (0.25, 0.22, 0.2, 1.0)
wall_bsdf.inputs['Roughness'].default_value = 0.7

wall_out = wall_nodes.new('ShaderNodeOutputMaterial')
wall_links.new(wall_bsdf.outputs['BSDF'], wall_out.inputs['Surface'])

wall1.data.materials.append(wall_mat)
wall2.data.materials.append(wall_mat)

# Create material for window (bright emitter simulating exterior light)
window_mat = bpy.data.materials.new("WindowMat")
window_mat.use_nodes = True
window_mat.node_tree.nodes.clear()
window_nodes = window_mat.node_tree.nodes
window_links = window_mat.node_tree.links

window_bsdf = window_nodes.new('ShaderNodeBsdfPrincipled')
window_bsdf.inputs['Base Color'].default_value = (1.0, 0.95, 0.85, 1.0)
window_bsdf.inputs['Emission'].default_value = (1.0, 0.95, 0.85, 1.0)
window_bsdf.inputs['Emission Strength'].default_value = 3.0

window_out = window_nodes.new('ShaderNodeOutputMaterial')
window_links.new(window_bsdf.outputs['BSDF'], window_out.inputs['Surface'])

window.data.materials.append(window_mat)

# Create volumetric fog cube (enclosing the scene)
bpy.ops.mesh.primitive_cube_add(size=30, location=(2, 2, 5))
fog_cube = bpy.context.active_object
fog_cube.name = "VolumeFog"

# Create volume material for fog
fog_mat = bpy.data.materials.new("FogMat")
fog_mat.use_nodes = True
fog_mat.node_tree.nodes.clear()
fog_nodes = fog_mat.node_tree.nodes
fog_links = fog_mat.node_tree.links

fog_volume = fog_nodes.new('ShaderNodeVolumeScatter')
fog_volume.inputs['Density'].default_value = 0.08
fog_volume.inputs['Color'].default_value = (0.8, 0.75, 0.7, 1.0)

fog_out = fog_nodes.new('ShaderNodeOutputMaterial')
fog_links.new(fog_volume.outputs['Volume'], fog_out.inputs['Volume'])

fog_cube.data.materials.append(fog_mat)

# Set world background to dark
world = bpy.data.worlds["World"]
world.use_nodes = True
world.node_tree.nodes["Background"].inputs['Color'].default_value = (0.05, 0.05, 0.08, 1.0)
world.node_tree.nodes["Background"].inputs['Strength'].default_value = 0.5

# Configure Eevee volumetrics
scene = bpy.context.scene
scene.eevee.volumetric_samples = 64
scene.eevee.use_volumetric_shadows = True
scene.eevee.volumetric_end = 100

# Set viewport shading to rendered
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'

print("Moody interior corner scene created successfully!")
