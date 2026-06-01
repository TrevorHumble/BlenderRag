import bpy
import bmesh
import random

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create ground plane
bpy.ops.mesh.primitive_grid_add(
    x_subdivisions=20,
    y_subdivisions=20,
    size=20.0,
    location=(0, 0, 0)
)
ground_plane = bpy.context.active_object
ground_plane.name = "Ground"

# Create a rough rock mesh using ico sphere with subdiv
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=1.0,
    location=(0, 20, 0)
)
rock_mesh_obj = bpy.context.active_object
rock_mesh_obj.name = "RockMesh"

# Add noise displacement to rock to make it rough
rock_obj = rock_mesh_obj
rock_data = rock_obj.data

# Apply a subdiv surface modifier to rock
subdiv_mod = rock_obj.modifiers.new(name="Subdivision", type='SUBSURF')
subdiv_mod.levels = 3

# Add a displacement modifier to rock using a simple noise texture
disp_mod = rock_obj.modifiers.new(name="Displacement", type='DISPLACE')
rock_mat = bpy.data.materials.new(name="RockMat")
rock_mat.use_nodes = True
nodes = rock_mat.node_tree.nodes
nodes.clear()
links = rock_mat.node_tree.links

bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
out_node = nodes.new(type='ShaderNodeOutputMaterial')
links.new(bsdf.outputs[0], out_node.inputs[0])

rock_obj.data.materials.append(rock_mat)

# Apply modifiers on rock to bake in the geometry
bpy.context.view_layer.objects.active = rock_obj
for mod in rock_obj.modifiers:
    bpy.ops.object.modifier_apply(modifier=mod.name)

# Create the scattering geometry nodes setup on ground plane
bpy.context.view_layer.objects.active = ground_plane
ground_plane.select_set(True)

# Add geometry nodes modifier
geom_mod = ground_plane.modifiers.new(name="RockScatter", type='NODES')

# Create node tree
tree = bpy.data.node_groups.new(name="RockScatterSetup", type='GeometryNodeTree')
geom_mod.node_group = tree

# Clear default nodes
tree.nodes.clear()

# Group input/output
group_in = tree.nodes.new(type='NodeGroupInput')
group_out = tree.nodes.new(type='NodeGroupOutput')

# Distribute Points on Faces
dist_points = tree.nodes.new(type='GeometryNodeDistributePointsOnFaces')
dist_points.distribute_method = 'POISSON'

# Create input for density
tree.inputs.new(type='NodeSocketInt', name='Density')
tree.inputs['Density'].default_value = 10

# Instance on Points
instance_node = tree.nodes.new(type='GeometryNodeInstanceOnPoints')

# Random value node for rotation randomization
random_rot_x = tree.nodes.new(type='GeometryNodeRandomValue')
random_rot_y = tree.nodes.new(type='GeometryNodeRandomValue')
random_rot_z = tree.nodes.new(type='GeometryNodeRandomValue')

# Set random ranges for rotations
random_rot_x.inputs[1].default_value = 0.0
random_rot_x.inputs[2].default_value = 6.28318
random_rot_y.inputs[1].default_value = 0.0
random_rot_y.inputs[2].default_value = 6.28318
random_rot_z.inputs[1].default_value = 0.0
random_rot_z.inputs[2].default_value = 6.28318

# Random value for scale
random_scale = tree.nodes.new(type='GeometryNodeRandomValue')
random_scale.inputs[1].default_value = 0.5
random_scale.inputs[2].default_value = 1.5

# Rotate Instances node
rotate_inst = tree.nodes.new(type='GeometryNodeRotateInstances')

# Scale Instances node
scale_inst = tree.nodes.new(type='GeometryNodeScaleInstances')

# Combine XYZ for rotation axis
combine_rot = tree.nodes.new(type='ShaderNodeCombineXYZ')

# Connect nodes
# Geometry input to distribute points
tree.links.new(group_in.outputs[0], dist_points.inputs[0])

# Density input to distribute points
tree.links.new(group_in.outputs['Density'], dist_points.inputs[1])

# Distributed points to instance on points
tree.links.new(dist_points.outputs[0], instance_node.inputs[0])

# Rock mesh object reference (hardcoded as object name)
# We use object info node to get the rock mesh
obj_info = tree.nodes.new(type='GeometryNodeObjectInfo')
obj_info.inputs[0].default_value = rock_obj
tree.links.new(obj_info.outputs[1], instance_node.inputs[1])

# Instance to rotate instances
tree.links.new(instance_node.outputs[0], rotate_inst.inputs[0])

# Random rotations to combine XYZ
tree.links.new(random_rot_x.outputs[1], combine_rot.inputs[0])
tree.links.new(random_rot_y.outputs[1], combine_rot.inputs[1])
tree.links.new(random_rot_z.outputs[1], combine_rot.inputs[2])

# Combined rotation to rotate instances (Euler rotation)
tree.links.new(combine_rot.outputs[0], rotate_inst.inputs[1])

# Rotate to scale instances
tree.links.new(rotate_inst.outputs[0], scale_inst.inputs[0])

# Random scale to scale instances
tree.links.new(random_scale.outputs[1], scale_inst.inputs[2])

# Scale output to group output
tree.links.new(scale_inst.outputs[0], group_out.inputs[0])

# Update scene
bpy.context.view_layer.update()
