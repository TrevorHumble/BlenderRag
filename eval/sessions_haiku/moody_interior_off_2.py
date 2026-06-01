import bpy
import bmesh
from mathutils import Vector, Matrix

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Set up scene and world
scene = bpy.context.scene
world = scene.world

# Configure world for volumetrics
world.use_nodes = True
world_nodes = world.node_tree.nodes
world_nodes.clear()
world_links = world.node_tree.links

bg_node = world_nodes.new(type='ShaderNodeBackground')
vol_node = world_nodes.new(type='ShaderNodeVolumePrincipled')
output_node = world_nodes.new(type='ShaderNodeOutputWorld')

bg_node.inputs['Strength'].default_value = 0.3
vol_node.inputs['Density'].default_value = 0.05
vol_node.inputs['Anisotropy'].default_value = 0.2

world_links.new(bg_node.outputs['Background'], output_node.inputs['Surface'])
world_links.new(vol_node.outputs['Volume'], output_node.inputs['Volume'])

# Set render engine to Eevee Next
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.eevee.use_volumetric_shadows = True

# Create floor
floor_mesh = bpy.data.meshes.new("FloorMesh")
floor_obj = bpy.data.objects.new("Floor", floor_mesh)
bpy.context.collection.objects.link(floor_obj)
bpy.context.view_layer.objects.active = floor_obj
floor_obj.select_set(True)

bm = bmesh.new()
bm.verts.new(Vector((0, 0, 0)))
bm.verts.new(Vector((10, 0, 0)))
bm.verts.new(Vector((10, 10, 0)))
bm.verts.new(Vector((0, 10, 0)))
bm.faces.new(bm.verts)
bm.to_mesh(floor_mesh)
bm.free()

# Create first wall (back)
wall1_mesh = bpy.data.meshes.new("Wall1Mesh")
wall1_obj = bpy.data.objects.new("Wall1", wall1_mesh)
bpy.context.collection.objects.link(wall1_obj)

bm = bmesh.new()
bm.verts.new(Vector((0, 10, 0)))
bm.verts.new(Vector((10, 10, 0)))
bm.verts.new(Vector((10, 10, 8)))
bm.verts.new(Vector((0, 10, 8)))
bm.faces.new(bm.verts)
bm.to_mesh(wall1_mesh)
bm.free()

# Create second wall (left side)
wall2_mesh = bpy.data.meshes.new("Wall2Mesh")
wall2_obj = bpy.data.objects.new("Wall2", wall2_mesh)
bpy.context.collection.objects.link(wall2_obj)

bm = bmesh.new()
bm.verts.new(Vector((0, 0, 0)))
bm.verts.new(Vector((0, 10, 0)))
bm.verts.new(Vector((0, 10, 8)))
bm.verts.new(Vector((0, 0, 8)))
bm.faces.new(bm.verts)
bm.to_mesh(wall2_mesh)
bm.free()

# Create window frame (simple quad)
window_mesh = bpy.data.meshes.new("WindowMesh")
window_obj = bpy.data.objects.new("Window", window_mesh)
bpy.context.collection.objects.link(window_obj)

bm = bmesh.new()
bm.verts.new(Vector((5, 10, 3)))
bm.verts.new(Vector((8, 10, 3)))
bm.verts.new(Vector((8, 10, 6)))
bm.verts.new(Vector((5, 10, 6)))
bm.faces.new(bm.verts)
bm.to_mesh(window_mesh)
bm.free()

# Create window glass material with emission
glass_mat = bpy.data.materials.new("WindowGlass")
glass_mat.use_nodes = True
glass_nodes = glass_mat.node_tree.nodes
glass_nodes.clear()
glass_links = glass_mat.node_tree.links

glass_bsdf = glass_nodes.new(type='ShaderNodePrincipled')
glass_output = glass_nodes.new(type='ShaderNodeOutputMaterial')

glass_bsdf.inputs['Base Color'].default_value = (0.7, 0.85, 1.0, 1.0)
glass_bsdf.inputs['Transmission'].default_value = 1.0
glass_bsdf.inputs['IOR'].default_value = 1.45
glass_bsdf.inputs['Roughness'].default_value = 0.05
glass_bsdf.inputs['Emission'].default_value = (0.8, 0.9, 1.0, 1.0)
glass_bsdf.inputs['Emission Strength'].default_value = 1.5

glass_links.new(glass_bsdf.outputs['BSDF'], glass_output.inputs['Surface'])

window_obj.data.materials.append(glass_mat)

# Create lamp object
lamp_data = bpy.data.lights.new("Lamp", type='POINT')
lamp_data.energy = 500
lamp_data.color = (1.0, 0.95, 0.85)

lamp_obj = bpy.data.objects.new("Lamp", lamp_data)
lamp_obj.location = (2, 3, 4)
bpy.context.collection.objects.link(lamp_obj)

# Add emissive material to lamp
lamp_mat = bpy.data.materials.new("LampEmissive")
lamp_mat.use_nodes = True
lamp_nodes = lamp_mat.node_tree.nodes
lamp_nodes.clear()
lamp_links = lamp_mat.node_tree.links

lamp_bsdf = lamp_nodes.new(type='ShaderNodePrincipled')
lamp_output = lamp_nodes.new(type='ShaderNodeOutputMaterial')

lamp_bsdf.inputs['Emission'].default_value = (1.0, 0.95, 0.8, 1.0)
lamp_bsdf.inputs['Emission Strength'].default_value = 2.0

lamp_links.new(lamp_bsdf.outputs['BSDF'], lamp_output.inputs['Surface'])

# Create a small sphere to represent the lamp bulb
bulb_mesh = bpy.data.meshes.new("BulbMesh")
bulb_obj = bpy.data.objects.new("Bulb", bulb_mesh)
bulb_obj.location = (2, 3, 4)
bpy.context.collection.objects.link(bulb_obj)

bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, radius=0.3, u_segments=16, v_segments=8)
bm.to_mesh(bulb_mesh)
bm.free()

bulb_obj.data.materials.append(lamp_mat)

# Create wall materials
wall_mat = bpy.data.materials.new("WallMaterial")
wall_mat.use_nodes = True
wall_nodes = wall_mat.node_tree.nodes
wall_nodes.clear()
wall_links = wall_mat.node_tree.links

wall_bsdf = wall_nodes.new(type='ShaderNodePrincipled')
wall_output = wall_nodes.new(type='ShaderNodeOutputMaterial')

wall_bsdf.inputs['Base Color'].default_value = (0.15, 0.12, 0.1, 1.0)
wall_bsdf.inputs['Roughness'].default_value = 0.8

wall_links.new(wall_bsdf.outputs['BSDF'], wall_output.inputs['Surface'])

wall1_obj.data.materials.append(wall_mat)
wall2_obj.data.materials.append(wall_mat)

# Create floor material
floor_mat = bpy.data.materials.new("FloorMaterial")
floor_mat.use_nodes = True
floor_nodes = floor_mat.node_tree.nodes
floor_nodes.clear()
floor_links = floor_mat.node_tree.links

floor_bsdf = floor_nodes.new(type='ShaderNodePrincipled')
floor_output = floor_nodes.new(type='ShaderNodeOutputMaterial')

floor_bsdf.inputs['Base Color'].default_value = (0.08, 0.06, 0.04, 1.0)
floor_bsdf.inputs['Roughness'].default_value = 0.85

floor_links.new(floor_bsdf.outputs['BSDF'], floor_output.inputs['Surface'])

floor_obj.data.materials.append(floor_mat)

# Set viewport shading
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'

print("Moody interior scene created successfully")
