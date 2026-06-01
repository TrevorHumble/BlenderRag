import bpy
import bmesh
from mathutils import Vector
import random

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create rocky base using UV Sphere with displacement
bpy.ops.mesh.primitive_uv_sphere_add(radius=3, location=(0, 0, 0))
base = bpy.context.active_object
base.name = "RockyBase"

# Add noise texture and use vertex groups for displacement
base_mesh = base.data
bm = bmesh.new()
bm.from_mesh(base_mesh)
bmesh.ops.subdivide_edges(bm, edges=bm.edges, number_cuts=2)
bm.to_mesh(base_mesh)
bm.free()
base_mesh.update()

# Add a material to the base for rocky look
mat_rock = bpy.data.materials.new(name="RockyMaterial")
mat_rock.use_nodes = True
mat_rock.node_tree.nodes.clear()
mat_rock.node_tree.nodes.new(type='ShaderNodePrincipled')
bsdf = mat_rock.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (0.4, 0.35, 0.3, 1.0)
bsdf.inputs['Roughness'].default_value = 0.8
base.data.materials.append(mat_rock)

# Create grass plane on top
bpy.ops.mesh.primitive_plane_add(size=5, location=(0, 0, 3.5))
grass_top = bpy.context.active_object
grass_top.name = "GrassTop"
grass_top.scale = (2.5, 2.5, 0.2)

mat_grass = bpy.data.materials.new(name="GrassMaterial")
mat_grass.use_nodes = True
mat_grass.node_tree.nodes.clear()
bsdf_grass = mat_grass.node_tree.nodes.new(type='ShaderNodePrincipled')
bsdf_grass.inputs['Base Color'].default_value = (0.2, 0.6, 0.2, 1.0)
bsdf_grass.inputs['Roughness'].default_value = 0.7
grass_top.data.materials.append(mat_grass)

# Create first low-poly tree
bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.3, radius2=0, depth=1.5, location=(-1.5, -1.5, 4.2))
tree1_trunk = bpy.context.active_object
tree1_trunk.name = "Tree1_Trunk"
tree1_trunk.scale = (0.3, 0.3, 1.0)

mat_trunk = bpy.data.materials.new(name="TrunkMaterial")
mat_trunk.use_nodes = True
mat_trunk.node_tree.nodes.clear()
bsdf_trunk = mat_trunk.node_tree.nodes.new(type='ShaderNodePrincipled')
bsdf_trunk.inputs['Base Color'].default_value = (0.4, 0.25, 0.1, 1.0)
bsdf_trunk.inputs['Roughness'].default_value = 0.75
tree1_trunk.data.materials.append(mat_trunk)

# Tree foliage (simple cone)
bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=1.0, radius2=0.2, depth=1.8, location=(-1.5, -1.5, 5.5))
tree1_foliage = bpy.context.active_object
tree1_foliage.name = "Tree1_Foliage"

mat_foliage = bpy.data.materials.new(name="FoliageMaterial")
mat_foliage.use_nodes = True
mat_foliage.node_tree.nodes.clear()
bsdf_foliage = mat_foliage.node_tree.nodes.new(type='ShaderNodePrincipled')
bsdf_foliage.inputs['Base Color'].default_value = (0.15, 0.5, 0.2, 1.0)
bsdf_foliage.inputs['Roughness'].default_value = 0.6
tree1_foliage.data.materials.append(mat_foliage)

# Create second tree
bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.25, radius2=0, depth=1.2, location=(1.5, 1.5, 4.2))
tree2_trunk = bpy.context.active_object
tree2_trunk.name = "Tree2_Trunk"
tree2_trunk.scale = (0.25, 0.25, 0.8)
tree2_trunk.data.materials.append(mat_trunk)

bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=0.9, radius2=0.15, depth=1.5, location=(1.5, 1.5, 5.3))
tree2_foliage = bpy.context.active_object
tree2_foliage.name = "Tree2_Foliage"
tree2_foliage.data.materials.append(mat_foliage)

# Set up lighting - soft daylight
bpy.ops.object.light_add(type='SUN', location=(5, 5, 8))
sun = bpy.context.active_object
sun.name = "Sunlight"
sun.data.energy = 2.0
sun.data.angle = 0.5

# Add a soft fill light
bpy.ops.object.light_add(type='SUN', location=(-3, -3, 6))
fill = bpy.context.active_object
fill.name = "FillLight"
fill.data.energy = 0.8
fill.data.angle = 0.3

# Set up world for soft lighting
world = bpy.data.worlds["World"]
world.use_nodes = True
world_nodes = world.node_tree.nodes
world_nodes.clear()
bg_node = world_nodes.new(type='ShaderNodeBackground')
bg_node.inputs['Color'].default_value = (0.85, 0.9, 1.0, 1.0)
bg_node.inputs['Strength'].default_value = 1.0
world_output = world_nodes.new(type='ShaderNodeOutputWorld')
world.node_tree.links.new(bg_node.outputs['Background'], world_output.inputs['Surface'])

# Set view transform to AgX
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.view_transform = 'AgX'

# Set render engine to Eevee Next and configure
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080

# Camera setup
bpy.ops.object.camera_add(location=(8, 8, 6))
camera = bpy.context.active_object
camera.name = "Camera"
scene.camera = camera
camera.rotation_euler = (1.1, 0, 0.785)
