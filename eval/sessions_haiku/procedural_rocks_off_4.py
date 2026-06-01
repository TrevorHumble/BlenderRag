import bpy
import bmesh
from mathutils import Vector
import random

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create ground plane
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "GroundPlane"

# Create a rough rock mesh
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 5))
rock_base = bpy.context.active_object
rock_base.name = "RockBase"

# Apply some displacement to the rock to make it rough
bm = bmesh.new()
bm.from_mesh(rock_base.data)

# Subdivide and displace vertices slightly to create roughness
for vert in bm.verts:
    noise_offset = random.uniform(-0.15, 0.15)
    vert.co += vert.co.normalized() * noise_offset

bm.to_mesh(rock_base.data)
bm.free()

rock_base.data.update()

# Apply a simple subdivision surface modifier for smoothness
subsurf = rock_base.modifiers.new(name="Subdivision", type='SUBSURF')
subsurf.levels = 2
subsurf.render_levels = 3

# Add geometry nodes to the ground plane
geometry_nodes = ground.modifiers.new(name="RockScatter", type='NODES')
node_group = bpy.data.node_groups.new("RockScatterGN", 'GeometryNodeTree')
geometry_nodes.node_group = node_group

# Clear default nodes
node_group.nodes.clear()

# Create nodes
nodes = node_group.nodes
links = node_group.links

# Input node
group_input = nodes.new('NodeGroupInput')
group_input.location = (-400, 0)

# Output node
group_output = nodes.new('NodeGroupOutput')
group_output.location = (800, 0)

# Distribute Points on Faces
distribute_points = nodes.new('GeometryNodeDistributePointsOnFaces')
distribute_points.location = (0, 200)
distribute_points.inputs['Density'].default_value = 2.0

# Random Value for rotation
random_rotation = nodes.new('FunctionNodeRandomValue')
random_rotation.location = (200, 400)
random_rotation.inputs['Min'].default_value = 0.0
random_rotation.inputs['Max'].default_value = 6.28318

# Random Value for scale
random_scale = nodes.new('FunctionNodeRandomValue')
random_scale.location = (200, 100)
random_scale.inputs['Min'].default_value = 0.7
random_scale.inputs['Max'].default_value = 1.5

# Instance on Points
instance_points = nodes.new('GeometryNodeInstanceOnPoints')
instance_points.location = (400, 100)

# Object Info node for the rock
object_info = nodes.new('GeometryNodeObjectInfo')
object_info.location = (200, -100)
object_info.inputs['Object'].default_value = rock_base

# Rotate Instances node
rotate_instances = nodes.new('GeometryNodeRotateInstances')
rotate_instances.location = (500, 200)

# Scale Instances node
scale_instances = nodes.new('GeometryNodeScaleInstances')
scale_instances.location = (600, 100)

# Connect nodes
# Ground geometry to Distribute Points
links.new(group_input.outputs['Geometry'], distribute_points.inputs['Mesh'])

# Distribute Points to Instance on Points
links.new(distribute_points.outputs['Points'], instance_points.inputs['Points'])

# Object Info to Instance on Points
links.new(object_info.outputs['Geometry'], instance_points.inputs['Instance'])

# Random values to rotation
links.new(random_rotation.outputs['Value'], rotate_instances.inputs['Rotation'].default_value)
links.new(distribute_points.outputs['Points'], rotate_instances.inputs['Instances'])

# Random scale to scale instances
links.new(random_scale.outputs['Value'], scale_instances.inputs['Scale'])
links.new(rotate_instances.outputs['Instances'], scale_instances.inputs['Instances'])

# Scale instances to output
links.new(scale_instances.outputs['Instances'], group_output.inputs['Geometry'])

# Apply the modifier to bake geometry
bpy.context.view_layer.objects.active = ground
bpy.ops.object.modifier_apply(modifier=geometry_nodes.name)

# Hide the rock base object
rock_base.hide_set(True)
rock_base.hide_render = True
