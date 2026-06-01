import bpy
import random
from mathutils import Euler, Vector
from bpy_extras.node_utils import connect_sockets

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create ground plane
bpy.ops.mesh.primitive_plane_add(size=20.0, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"

# Create a rough rock mesh using an ico sphere with displacement
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0, location=(0, 0, 10))
rock_base = bpy.context.active_object
rock_base.name = "RockBase"

# Add a displacement modifier to make the rock rougher
displace_mod = rock_base.modifiers.new(name="Displace", type='DISPLACE')
displace_mod.strength = 0.3

# Create a new geometry node modifier on the ground plane
bpy.context.view_layer.objects.active = ground
bpy.ops.node.new_geometry_nodes_modifier()

# Get the geometry node tree
geom_mod = ground.modifiers[-1]
node_tree = geom_mod.node_group

# Clear default nodes
node_tree.nodes.clear()
node_tree.links.clear()

# Create input/output nodes
group_input = node_tree.nodes.new(type='NodeGroupInput')
group_output = node_tree.nodes.new(type='NodeGroupOutput')

# Create distribute points on faces node
dist_points_node = node_tree.nodes.new(type='GeometryNodeDistributePointsOnFaces')
dist_points_node.distribute_method = 'RANDOM'
dist_points_node.inputs['Density'].default_value = 0.5

# Create instance on points node
instance_node = node_tree.nodes.new(type='GeometryNodeInstanceOnPoints')

# Create random value nodes for rotation and scale
random_rot_x = node_tree.nodes.new(type='GeometryNodeRandomValue')
random_rot_x.inputs['Min'].default_value = 0.0
random_rot_x.inputs['Max'].default_value = 6.28
random_rot_x.data_type = 'FLOAT'

random_rot_y = node_tree.nodes.new(type='GeometryNodeRandomValue')
random_rot_y.inputs['Min'].default_value = 0.0
random_rot_y.inputs['Max'].default_value = 6.28
random_rot_y.data_type = 'FLOAT'

random_rot_z = node_tree.nodes.new(type='GeometryNodeRandomValue')
random_rot_z.inputs['Min'].default_value = 0.0
random_rot_z.inputs['Max'].default_value = 6.28
random_rot_z.data_type = 'FLOAT'

random_scale = node_tree.nodes.new(type='GeometryNodeRandomValue')
random_scale.inputs['Min'].default_value = 0.7
random_scale.inputs['Max'].default_value = 1.3
random_scale.data_type = 'FLOAT'

# Create rotation and scale nodes
rotate_node = node_tree.nodes.new(type='GeometryNodeRotateInstances')
scale_node = node_tree.nodes.new(type='GeometryNodeScaleInstances')

# Connect the nodes
connect_sockets(dist_points_node.inputs['Mesh'], group_input.outputs['Geometry'])
connect_sockets(instance_node.inputs['Points'], dist_points_node.outputs['Points'])
connect_sockets(instance_node.inputs['Instance'], group_input.outputs['Geometry'])

# Connect rotation inputs
connect_sockets(rotate_node.inputs['Instances'], instance_node.outputs['Instances'])
connect_sockets(rotate_node.inputs['Rotation'], random_rot_x.outputs['Value'])

# Connect scale node
connect_sockets(scale_node.inputs['Instances'], rotate_node.outputs['Instances'])
connect_sockets(scale_node.inputs['Scale'], random_scale.outputs['Value'])

# Connect to output
connect_sockets(group_output.inputs['Geometry'], scale_node.outputs['Instances'])

# Set the rock mesh as the instance geometry
# This is done by setting the modifier's node group input to use the rock
geom_mod.node_group.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeTreeInterfaceSocketGeometry')

# Now hide the rock base mesh from viewport and rendering
rock_base.hide_set(True)
rock_base.hide_render = True

# Optional: Add material to ground for visibility
mat = bpy.data.materials.new(name="GroundMat")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.3, 0.3, 0.25, 1.0)
ground.data.materials.append(mat)

# Create material for rocks
rock_mat = bpy.data.materials.new(name="RockMat")
rock_mat.use_nodes = True
rock_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.4, 0.35, 0.3, 1.0)
rock_mat.node_tree.nodes["Principled BSDF"].inputs['Roughness'].default_value = 0.8
rock_base.data.materials.append(rock_mat)
