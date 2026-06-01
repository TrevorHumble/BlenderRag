import bpy
import bmesh
from mathutils import Matrix, Vector
import random

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create ground plane
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"

# Create a rock mesh (icosphere with random displacement for roughness)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(10, 0, 0))
rock_base = bpy.context.active_object
rock_base.name = "RockBase"

# Add roughness to rock using subdivision and displacement
bpy.ops.object.modifier_add(type='SUBDIVISION')
rock_base.modifiers[-1].levels = 2

# Apply a simple noise-based roughness via geometry nodes
bpy.ops.object.modifier_add(type='NODES')
geom_mod = rock_base.modifiers[-1]
node_group = bpy.data.node_groups.new(name="RockRoughness", type='GEOMETRY')
geom_mod.node_group = node_group

# Setup node group inputs/outputs
node_group.inputs.new('NodeSocketGeometry', 'Geometry')
node_group.outputs.new('NodeSocketGeometry', 'Geometry')

# Add nodes for roughness
nodes = node_group.nodes
links = node_group.links
nodes.clear()

input_node = nodes.new('NodeGroupInput')
output_node = nodes.new('NodeGroupOutput')

# Add noise to displace vertices
noise_node = nodes.new('ShaderNodeTexNoise')
noise_node.inputs['Scale'].default_value = 5.0

displace_node = nodes.new('GeometryNodeDisplace')
displace_node.inputs['Displacement'].default_value = 0.08

links.new(input_node.outputs['Geometry'], displace_node.inputs['Geometry'])
links.new(displace_node.outputs['Geometry'], output_node.inputs['Geometry'])

# Hide rock base from viewport
rock_base.hide_set(True)
rock_base.hide_render = True

# Switch to ground plane for geometry nodes setup
bpy.context.view_layer.objects.active = ground
ground.select_set(True)

# Add geometry nodes to ground for scattering
bpy.ops.object.modifier_add(type='NODES')
scatter_mod = ground.modifiers[-1]
scatter_mod.name = "RockScatter"

# Create main scatter node group
scatter_group = bpy.data.node_groups.new(name="RockScatter", type='GEOMETRY')
scatter_mod.node_group = scatter_group

# Setup node group
scatter_group.inputs.new('NodeSocketGeometry', 'Geometry')
scatter_group.outputs.new('NodeSocketGeometry', 'Geometry')

nodes = scatter_group.nodes
links = scatter_group.links
nodes.clear()

# Create node graph for scattering
input_node = nodes.new('NodeGroupInput')
output_node = nodes.new('NodeGroupOutput')

# Distribute points on surface
distribute_node = nodes.new('GeometryNodeDistributePointsOnFaces')
distribute_node.inputs['Density'].default_value = 0.5
distribute_node.inputs['Seed'].default_value = 42

# Instance on points
instance_node = nodes.new('GeometryNodeInstanceOnPoints')

# Add random rotation
rotate_node = nodes.new('GeometryNodeRandomValue')
rotate_node.data_type = 'FLOAT_VECTOR'
rotate_node.inputs['Max'].default_value = (6.28, 6.28, 6.28)

# Add random scale
scale_node = nodes.new('GeometryNodeRandomValue')
scale_node.data_type = 'FLOAT'
scale_node.inputs['Min'].default_value = 0.6
scale_node.inputs['Max'].default_value = 1.4

# Rotation to euler node
rot_euler = nodes.new('FunctionNodeRotateEuler')

# Transform node for rotation
transform_node = nodes.new('GeometryNodeTransform')

# Scale via transform
scale_transform = nodes.new('GeometryNodeTransform')

# Object info for rock reference
object_info = nodes.new('GeometryNodeObjectInfo')
object_info.inputs['Object'].default_value = rock_base

# Connect nodes
links.new(input_node.outputs['Geometry'], distribute_node.inputs['Geometry'])
links.new(distribute_node.outputs['Points'], instance_node.inputs['Points'])
links.new(object_info.outputs['Geometry'], instance_node.inputs['Instance'])

# Random rotations
links.new(distribute_node.outputs['Points'], rotate_node.inputs['Seed'])
links.new(rotate_node.outputs['Value'], rot_euler.inputs['Rotation'])
links.new(rot_euler.outputs['Rotation'], instance_node.inputs['Rotation'])

# Random scales
links.new(distribute_node.outputs['Points'], scale_node.inputs['Seed'])
links.new(instance_node.outputs['Instances'], scale_transform.inputs['Geometry'])
links.new(scale_node.outputs['Value'], scale_transform.inputs['Scale'])

# Join geometry
join_node = nodes.new('GeometryNodeJoinGeometry')
links.new(scale_transform.outputs['Geometry'], join_node.inputs['Geometry'])

# Output
links.new(join_node.outputs['Geometry'], output_node.inputs['Geometry'])

# Set viewport and render settings
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'SOLID'

bpy.context.view_layer.update()
