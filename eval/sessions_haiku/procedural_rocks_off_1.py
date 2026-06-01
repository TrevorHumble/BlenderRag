import bpy
import bmesh
from mathutils import Vector, Matrix
import random

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create ground plane
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"
ground.scale = (10, 10, 1)
bpy.ops.object.transform_apply(scale=True)

# Create a rough rock mesh (icosphere with subdiv and noise displacement)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, -5))
rock_base = bpy.context.active_object
rock_base.name = "RockBase"

# Add subdivision surface modifier for smoothness
subdiv = rock_base.modifiers.new(name="Subdivision", type='SUBSURF')
subdiv.levels = 2
subdiv.render_levels = 3

# Add displace modifier for roughness
displace = rock_base.modifiers.new(name="Displace", type='DISPLACE')
# Create simple noise texture for displacement
noise_tex = bpy.data.textures.new(name="RockNoise", type='CLOUDS')
noise_tex.cloud_type = 'COLOR'
noise_tex.scale = 2.0
displace.texture = noise_tex
displace.strength = 0.3

# Apply material to rock
mat = bpy.data.materials.new(name="RockMaterial")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs['Base Color'].default_value = (0.4, 0.35, 0.3, 1.0)
bsdf.inputs['Roughness'].default_value = 0.8
rock_base.data.materials.append(mat)

# Create scatter object with geometry nodes
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
scatter_obj = bpy.context.active_object
scatter_obj.name = "RockScatter"

# Add geometry nodes modifier
gn_mod = scatter_obj.modifiers.new(name="GeoNodes", type='GEOMETRY')
gn_tree = bpy.data.node_groups.new(type="GeometryNodeTree", name="RockScatterTree")
gn_mod.node_group = gn_tree

# Link object to modifier for instance reference
gn_mod.node_group.inputs.new(name="RockMesh", socket_type='OBJECT')
gn_mod["Socket_0"] = rock_base

# Set up geometry node tree
nodes = gn_tree.nodes
links = gn_tree.links
nodes.clear()

# Input node
input_node = nodes.new(type="NodeGroupInput")
input_node.location = (-400, 0)

# Output node
output_node = nodes.new(type="NodeGroupOutput")
output_node.location = (800, 0)

# Distribute Points on Face
dist_points = nodes.new(type="GeometryNodeDistributePointsOnFaces")
dist_points.location = (0, 200)
dist_points.inputs['Density'].default_value = 5.0

# Instance on Points node
instance_node = nodes.new(type="GeometryNodeInstanceOnPoints")
instance_node.location = (200, 100)

# Random Value node for rotation (X)
rand_rot_x = nodes.new(type="FunctionNodeRandomValue")
rand_rot_x.location = (0, -100)
rand_rot_x.inputs['Min'].default_value = 0.0
rand_rot_x.inputs['Max'].default_value = 6.28318

# Random Value node for rotation (Y)
rand_rot_y = nodes.new(type="FunctionNodeRandomValue")
rand_rot_y.location = (0, -200)
rand_rot_y.inputs['Min'].default_value = 0.0
rand_rot_y.inputs['Max'].default_value = 6.28318

# Random Value node for rotation (Z)
rand_rot_z = nodes.new(type="FunctionNodeRandomValue")
rand_rot_z.location = (0, -300)
rand_rot_z.inputs['Min'].default_value = 0.0
rand_rot_z.inputs['Max'].default_value = 6.28318

# Random Value node for scale
rand_scale = nodes.new(type="FunctionNodeRandomValue")
rand_scale.location = (0, -400)
rand_scale.inputs['Min'].default_value = 0.6
rand_scale.inputs['Max'].default_value = 1.4

# Combine XYZ for rotation
combine_rot = nodes.new(type="ShaderNodeCombineXYZ")
combine_rot.location = (200, -200)

# Set Position node for rotation
set_position_rot = nodes.new(type="GeometryNodeSetPosition")
set_position_rot.location = (400, 0)

# Distribute Points connection
links.new(input_node.outputs['Geometry'], dist_points.inputs['Mesh'])

# Connect to Instance on Points
links.new(dist_points.outputs['Points'], instance_node.inputs['Points'])
links.new(input_node.outputs['Socket_0'], instance_node.inputs['Instance'])

# Random values for rotation
links.new(dist_points.outputs['Points'], rand_rot_x.inputs['ID'])
links.new(dist_points.outputs['Points'], rand_rot_y.inputs['ID'])
links.new(dist_points.outputs['Points'], rand_rot_z.inputs['ID'])
links.new(dist_points.outputs['Points'], rand_scale.inputs['ID'])

# Combine rotations
links.new(rand_rot_x.outputs['Value'], combine_rot.inputs['X'])
links.new(rand_rot_y.outputs['Value'], combine_rot.inputs['Y'])
links.new(rand_rot_z.outputs['Value'], combine_rot.inputs['Z'])

# Set rotation on instances
links.new(instance_node.outputs['Instances'], set_position_rot.inputs['Geometry'])
links.new(combine_rot.outputs['Vector'], set_position_rot.inputs['Rotation'])

# Scale instances via Transform node
scale_node = nodes.new(type="GeometryNodeTransform")
scale_node.location = (500, 0)
links.new(set_position_rot.outputs['Geometry'], scale_node.inputs['Geometry'])
links.new(rand_scale.outputs['Value'], scale_node.inputs['Scale'])

# Output
links.new(scale_node.outputs['Geometry'], output_node.inputs['Geometry'])

# Set viewport shading to show results
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'
