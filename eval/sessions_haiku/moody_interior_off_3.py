import bpy
from mathutils import Vector, Matrix
import math

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Set world settings for atmosphere
world = bpy.data.worlds['World']
world.use_nodes = True
world_nodes = world.node_tree.nodes
world_nodes.clear()
world_links = world.node_tree.links

# Add background shader for ambient light
bg_node = world_nodes.new(type='ShaderNodeBackground')
bg_node.inputs['Strength'].default_value = 0.3

# Add volume scatter for volumetric effects
volume_node = world_nodes.new(type='ShaderNodeVolumeScatter')
volume_node.inputs['Density'].default_value = 0.05
volume_node.inputs['Anisotropy'].default_value = 0.5

output_node = world_nodes.new(type='ShaderNodeWorldOutput')
world_links.new(bg_node.outputs['Background'], output_node.inputs['Surface'])
world_links.new(volume_node.outputs['Volume'], output_node.inputs['Volume'])

# Create floor
floor_mesh = bpy.data.meshes.new('FloorMesh')
floor_verts = [
    (-5, -5, 0),
    (5, -5, 0),
    (5, 5, 0),
    (-5, 5, 0),
]
floor_faces = [(0, 1, 2, 3)]
floor_mesh.from_pydata(floor_verts, [], floor_faces)
floor_mesh.update()
floor_obj = bpy.data.objects.new('Floor', floor_mesh)
bpy.context.collection.objects.link(floor_obj)

# Add floor material
floor_mat = bpy.data.materials.new('FloorMaterial')
floor_mat.use_nodes = True
floor_nodes = floor_mat.node_tree.nodes
floor_nodes.clear()
floor_links = floor_mat.node_tree.links
floor_bsdf = floor_nodes.new(type='ShaderNodeBsdfPrincipled')
floor_bsdf.inputs['Base Color'].default_value = (0.2, 0.2, 0.2, 1.0)
floor_bsdf.inputs['Roughness'].default_value = 0.8
floor_out = floor_nodes.new(type='ShaderNodeOutputMaterial')
floor_links.new(floor_bsdf.outputs['BSDF'], floor_out.inputs['Surface'])
floor_obj.data.materials.append(floor_mat)

# Create left wall
left_wall_mesh = bpy.data.meshes.new('LeftWallMesh')
left_wall_verts = [
    (-5, -5, 0),
    (-5, 5, 0),
    (-5, 5, 3),
    (-5, -5, 3),
]
left_wall_faces = [(0, 1, 2, 3)]
left_wall_mesh.from_pydata(left_wall_verts, [], left_wall_faces)
left_wall_mesh.update()
left_wall_obj = bpy.data.objects.new('LeftWall', left_wall_mesh)
bpy.context.collection.objects.link(left_wall_obj)

# Add left wall material
left_wall_mat = bpy.data.materials.new('WallMaterial')
left_wall_mat.use_nodes = True
left_wall_nodes = left_wall_mat.node_tree.nodes
left_wall_nodes.clear()
left_wall_links = left_wall_mat.node_tree.links
left_wall_bsdf = left_wall_nodes.new(type='ShaderNodeBsdfPrincipled')
left_wall_bsdf.inputs['Base Color'].default_value = (0.3, 0.25, 0.25, 1.0)
left_wall_bsdf.inputs['Roughness'].default_value = 0.85
left_wall_out = left_wall_nodes.new(type='ShaderNodeOutputMaterial')
left_wall_links.new(left_wall_bsdf.outputs['BSDF'], left_wall_out.inputs['Surface'])
left_wall_obj.data.materials.append(left_wall_mat)

# Create back wall
back_wall_mesh = bpy.data.meshes.new('BackWallMesh')
back_wall_verts = [
    (-5, 5, 0),
    (5, 5, 0),
    (5, 5, 3),
    (-5, 5, 3),
]
back_wall_faces = [(0, 1, 2, 3)]
back_wall_mesh.from_pydata(back_wall_verts, [], back_wall_faces)
back_wall_mesh.update()
back_wall_obj = bpy.data.objects.new('BackWall', back_wall_mesh)
bpy.context.collection.objects.link(back_wall_obj)
back_wall_obj.data.materials.append(left_wall_mat)

# Create window frame
window_frame_mesh = bpy.data.meshes.new('WindowFrameMesh')
# Outer frame
window_frame_verts = [
    (2, 4.9, 1.2),
    (4, 4.9, 1.2),
    (4, 4.9, 2.5),
    (2, 4.9, 2.5),
]
window_frame_faces = [(0, 1, 2, 3)]
window_frame_mesh.from_pydata(window_frame_verts, [], window_frame_faces)
window_frame_mesh.update()
window_frame_obj = bpy.data.objects.new('WindowFrame', window_frame_mesh)
bpy.context.collection.objects.link(window_frame_obj)

# Add window frame material
frame_mat = bpy.data.materials.new('FrameMaterial')
frame_mat.use_nodes = True
frame_nodes = frame_mat.node_tree.nodes
frame_nodes.clear()
frame_links = frame_mat.node_tree.links
frame_bsdf = frame_nodes.new(type='ShaderNodeBsdfPrincipled')
frame_bsdf.inputs['Base Color'].default_value = (0.15, 0.15, 0.15, 1.0)
frame_bsdf.inputs['Metallic'].default_value = 0.3
frame_out = frame_nodes.new(type='ShaderNodeOutputMaterial')
frame_links.new(frame_bsdf.outputs['BSDF'], frame_out.inputs['Surface'])
window_frame_obj.data.materials.append(frame_mat)

# Create window glass (emissive to simulate light streaming in)
glass_mesh = bpy.data.meshes.new('GlassMesh')
glass_verts = [
    (2.1, 4.85, 1.3),
    (3.9, 4.85, 1.3),
    (3.9, 4.85, 2.4),
    (2.1, 4.85, 2.4),
]
glass_faces = [(0, 1, 2, 3)]
glass_mesh.from_pydata(glass_verts, [], glass_faces)
glass_mesh.update()
glass_obj = bpy.data.objects.new('WindowGlass', glass_mesh)
bpy.context.collection.objects.link(glass_obj)

# Add glass material with emission
glass_mat = bpy.data.materials.new('GlassMaterial')
glass_mat.use_nodes = True
glass_nodes = glass_mat.node_tree.nodes
glass_nodes.clear()
glass_links = glass_mat.node_tree.links
glass_bsdf = glass_nodes.new(type='ShaderNodeBsdfPrincipled')
glass_bsdf.inputs['Base Color'].default_value = (0.6, 0.7, 0.8, 1.0)
glass_bsdf.inputs['Transmission'].default_value = 1.0
glass_bsdf.inputs['IOR'].default_value = 1.5
emission_node = glass_nodes.new(type='ShaderNodeEmission')
emission_node.inputs['Color'].default_value = (0.8, 0.85, 1.0, 1.0)
emission_node.inputs['Strength'].default_value = 2.0
mix_shader = glass_nodes.new(type='ShaderNodeMix')
mix_shader.data_type = 'SHADER'
glass_out = glass_nodes.new(type='ShaderNodeOutputMaterial')
glass_links.new(glass_bsdf.outputs['BSDF'], mix_shader.inputs[1])
glass_links.new(emission_node.outputs['Emission'], mix_shader.inputs[2])
glass_links.new(mix_shader.outputs['Result'], glass_out.inputs['Surface'])
glass_obj.data.materials.append(glass_mat)

# Create table (simple geometry)
table_mesh = bpy.data.meshes.new('TableMesh')
table_verts = [
    (-2, -2, 0.7),
    (1, -2, 0.7),
    (1, 1, 0.7),
    (-2, 1, 0.7),
    (-2, -2, 0),
    (1, -2, 0),
    (1, 1, 0),
    (-2, 1, 0),
]
table_faces = [
    (0, 1, 2, 3),  # top
    (4, 5, 6, 7),  # bottom
    (0, 1, 5, 4),  # sides
    (1, 2, 6, 5),
    (2, 3, 7, 6),
    (3, 0, 4, 7),
]
table_mesh.from_pydata(table_verts, [], table_faces)
table_mesh.update()
table_obj = bpy.data.objects.new('Table', table_mesh)
bpy.context.collection.objects.link(table_obj)

# Add table material
table_mat = bpy.data.materials.new('TableMaterial')
table_mat.use_nodes = True
table_nodes = table_mat.node_tree.nodes
table_nodes.clear()
table_links = table_mat.node_tree.links
table_bsdf = table_nodes.new(type='ShaderNodeBsdfPrincipled')
table_bsdf.inputs['Base Color'].default_value = (0.4, 0.3, 0.2, 1.0)
table_bsdf.inputs['Roughness'].default_value = 0.6
table_out = table_nodes.new(type='ShaderNodeOutputMaterial')
table_links.new(table_bsdf.outputs['BSDF'], table_out.inputs['Surface'])
table_obj.data.materials.append(table_mat)

# Create emissive lamp (standing lamp)
lamp_base_mesh = bpy.data.meshes.new('LampBaseMesh')
lamp_base_verts = [
    (-3, -3, 0),
    (-3.3, -3, 0),
    (-3.3, -3.3, 0),
    (-3, -3.3, 0),
    (-3, -3, 0.4),
    (-3.3, -3, 0.4),
    (-3.3, -3.3, 0.4),
    (-3, -3.3, 0.4),
]
lamp_base_faces = [
    (0, 1, 2, 3),
    (4, 5, 6, 7),
    (0, 1, 5, 4),
    (1, 2, 6, 5),
    (2, 3, 7, 6),
    (3, 0, 4, 7),
]
lamp_base_mesh.from_pydata(lamp_base_verts, [], lamp_base_faces)
lamp_base_mesh.update()
lamp_base_obj = bpy.data.objects.new('LampBase', lamp_base_mesh)
bpy.context.collection.objects.link(lamp_base_obj)

# Add lamp base material
lamp_base_mat = bpy.data.materials.new('LampBaseMaterial')
lamp_base_mat.use_nodes = True
lamp_base_nodes = lamp_base_mat.node_tree.nodes
lamp_base_nodes.clear()
lamp_base_links = lamp_base_mat.node_tree.links
lamp_base_bsdf = lamp_base_nodes.new(type='ShaderNodeBsdfPrincipled')
lamp_base_bsdf.inputs['Base Color'].default_value = (0.25, 0.2, 0.15, 1.0)
lamp_base_bsdf.inputs['Metallic'].default_value = 0.1
lamp_base_out = lamp_base_nodes.new(type='ShaderNodeOutputMaterial')
lamp_base_links.new(lamp_base_bsdf.outputs['BSDF'], lamp_base_out.inputs['Surface'])
lamp_base_obj.data.materials.append(lamp_base_mat)

# Create lamp shade (emissive cylinder)
lamp_shade_mesh = bpy.data.meshes.new('LampShadeMesh')
# Simple cylinder approximation
verts = []
edges = []
faces = []
segments = 8
for i in range(segments):
    angle = (i / segments) * 2 * math.pi
    x = -3.15 + 0.35 * math.cos(angle)
    y = -3.15 + 0.35 * math.sin(angle)
    verts.append((x, y, 1.8))
for i in range(segments):
    angle = (i / segments) * 2 * math.pi
    x = -3.15 + 0.35 * math.cos(angle)
    y = -3.15 + 0.35 * math.sin(angle)
    verts.append((x, y, 2.3))
for i in range(segments - 1):
    faces.append((i, i + 1, segments + i + 1, segments + i))
faces.append((segments - 1, 0, segments, 2 * segments - 1))
lamp_shade_mesh.from_pydata(verts, [], faces)
lamp_shade_mesh.update()
lamp_shade_obj = bpy.data.objects.new('LampShade', lamp_shade_mesh)
bpy.context.collection.objects.link(lamp_shade_obj)

# Add emissive lamp material
lamp_mat = bpy.data.materials.new('LampMaterial')
lamp_mat.use_nodes = True
lamp_nodes = lamp_mat.node_tree.nodes
lamp_nodes.clear()
lamp_links = lamp_mat.node_tree.links
lamp_emission = lamp_nodes.new(type='ShaderNodeEmission')
lamp_emission.inputs['Color'].default_value = (1.0, 0.95, 0.8, 1.0)
lamp_emission.inputs['Strength'].default_value = 3.5
lamp_out = lamp_nodes.new(type='ShaderNodeOutputMaterial')
lamp_links.new(lamp_emission.outputs['Emission'], lamp_out.inputs['Surface'])
lamp_shade_obj.data.materials.append(lamp_mat)

# Set render engine to Eevee Next for volumetrics
for scene in bpy.data.scenes:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.eevee.use_volumetric_scatter = True
    scene.eevee.volumetric_scatter_anisotropy = 0.5
    scene.eevee.volumetric_start_distance = 0.1
    scene.eevee.volumetric_end_distance = 20.0

# Set viewport shading to rendered for best preview
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'

# Frame all objects in view
bpy.ops.view3d.view_all(center=True)

print("Moody interior corner scene created successfully with volumetrics.")