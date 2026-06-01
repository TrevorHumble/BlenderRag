import bpy
import bmesh
import random
from mathutils import Vector, Euler

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create ground plane
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "GroundPlane"

# Create a simple rock mesh procedurally
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(10, 10, 1))
rock_base = bpy.context.active_object
rock_base.name = "RockBase"

# Deform the sphere to make it more rock-like
bpy.context.view_layer.objects.active = rock_base
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.transform.resize(value=(1.2, 0.9, 1.1))
bpy.ops.object.mode_set(mode='OBJECT')

# Apply a simple noise modifier for roughness
noise_modifier = rock_base.modifiers.new(name="Noise", type='DISPLACE')
noise_texture = bpy.data.textures.new("RockNoise", type='CLOUDS')
noise_modifier.texture = noise_texture
noise_modifier.strength = 0.3

# Create a new object for the scattered rocks (will use geometry nodes)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -5))
scatter_obj = bpy.context.active_object
scatter_obj.name = "RockScatter"

# Add geometry node modifier to scatter_obj
geo_modifier = scatter_obj.modifiers.new(name="RockScatter", type='GEOMETRY')
geo_modifier.node_group = bpy.data.node_groups.new(name="RockScatterNodes", type='GEOMETRY')

# Build the node tree
node_group = geo_modifier.node_group
nodes = node_group.nodes
links = node_group.links

# Clear default nodes
nodes.clear()

# Create Group Input and Output
group_input = nodes.new(type='NodeGroupInput')
group_output = nodes.new(type='NodeGroupOutput')

# Distribute Points on Faces
distribute_points = nodes.new(type='GeometryNodeDistributePointsOnFaces')
distribute_points.inputs['Density'].default_value = 2.0

# Instance on Points
instance_node = nodes.new(type='GeometryNodeInstanceOnPoints')

# Rotation Randomizer (Random Value for each axis)
random_rot_x = nodes.new(type='GeometryNodeInputRandomValue')
random_rot_x.data_type = 'FLOAT_VECTOR'
random_rot_x.inputs['Min'].default_value = (0.0, 0.0, 0.0)
random_rot_x.inputs['Max'].default_value = (6.28, 6.28, 6.28)

# Scale Randomizer
random_scale = nodes.new(type='GeometryNodeInputRandomValue')
random_scale.data_type = 'FLOAT'
random_scale.inputs['Min'].default_value = 0.6
random_scale.inputs['Max'].default_value = 1.5

# Rotation node (combine euler)
rotate_node = nodes.new(type='FunctionNodeRotateEuler')
rotate_node.rotation_type = 'EULER_XYZ'

# Scale node
scale_node = nodes.new(type='GeometryNodeScale')

# Realize Instances
realize = nodes.new(type='GeometryNodeRealizeInstances')

# Connect geometry inputs/outputs to group
group_input.outputs['Geometry'].link(distribute_points.inputs['Mesh'])
distribute_points.outputs['Points'].link(instance_node.inputs['Points'])

# Link the rock base object reference
instance_node.inputs['Instance'].default_value = rock_base

# Connect randomizers to instance transformations
random_rot_x.outputs['Value'].link(rotate_node.inputs['Rotation'])
random_scale.outputs['Value'].link(scale_node.inputs['Scale'])

# Connect instance to transforms
instance_node.outputs['Instances'].link(rotate_node.inputs['Geometry'])
rotate_node.outputs['Geometry'].link(scale_node.inputs['Geometry'])

# Connect scale output to realize
scale_node.outputs['Geometry'].link(realize.inputs['Geometry'])

# Connect to output
realize.outputs['Geometry'].link(group_output.inputs['Geometry'])

# Select ground plane as active and apply modifier to it instead
bpy.context.view_layer.objects.active = ground
geo_mod_ground = ground.modifiers.new(name="RockScatter", type='GEOMETRY')
geo_mod_ground.node_group = geo_modifier.node_group

# Unhide the rock base for instancing
rock_base.hide_set(False)
rock_base.hide_render = False

# Set viewport shading to see result better
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'SOLID'

print("Rock scatter setup complete")
