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
ground.name = "GroundPlane"

# Create a rough rock mesh using icosphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 5))
rock_base = bpy.context.active_object
rock_base.name = "RockBase"

# Subdivide the rock to make it rough
bpy.context.view_layer.objects.active = rock_base
bpy.ops.object.shade_smooth()

# Add displacement modifier to make rock rougher
displacement_modifier = rock_base.modifiers.new(name="Displacement", type='DISPLACE')
displacement_modifier.strength = 0.3

# Create a simple texture for displacement
texture = bpy.data.textures.new(name="RockTexture", type='CLOUDS')
texture.cloud_type = 'COLOR'
displacement_modifier.texture = texture

# Create geometry node tree for scattering
bpy.context.view_layer.objects.active = ground
bpy.ops.object.modifier_add(type='NODES')
modifier = ground.modifiers[-1]
modifier.name = "RockScatter"

# Get or create node group
if modifier.node_group is None:
    node_group = bpy.data.node_groups.new(name="RockScatterGroup", type='GeometryNodeTree')
    modifier.node_group = node_group
else:
    node_group = modifier.node_group

# Clear default nodes
node_group.nodes.clear()

# Create nodes
nodes = node_group.nodes
links = node_group.links

# Group Input node
group_input = nodes.new(type='NodeGroupInput')
group_input.location = (-400, 0)

# Distribute Points on Faces
distribute_points = nodes.new(type='GeometryNodeDistributePointsOnFaces')
distribute_points.location = (-200, 0)
distribute_points.inputs['Density'].default_value = 2.0

# Point Instance node
point_instance = nodes.new(type='GeometryNodeInstanceOnPoints')
point_instance.location = (100, 0)

# Random Value node for scale
random_scale = nodes.new(type='FunctionNodeRandomValue')
random_scale.location = (-200, -200)
random_scale.inputs['Min'].default_value = 0.5
random_scale.inputs['Max'].default_value = 1.5
random_scale.data_type = 'FLOAT'

# Random Value node for rotation
random_rotation = nodes.new(type='FunctionNodeRandomValue')
random_rotation.location = (-200, -350)
random_rotation.inputs['Min'].default_value = Vector((0, 0, 0))
random_rotation.inputs['Max'].default_value = Vector((6.28, 6.28, 6.28))
random_rotation.data_type = 'FLOAT_VECTOR'

# Rotate Instances node
rotate_instances = nodes.new(type='GeometryNodeRotateInstances')
rotate_instances.location = (250, 0)

# Scale Instances node
scale_instances = nodes.new(type='GeometryNodeScaleInstances')
scale_instances.location = (400, 0)

# Realize Instances node
realize_instances = nodes.new(type='GeometryNodeRealizeInstances')
realize_instances.location = (550, 0)

# Group Output node
group_output = nodes.new(type='NodeGroupOutput')
group_output.location = (700, 0)

# Create sockets for group input/output
group_input.outputs['Geometry'].name = 'Geometry'
group_output.inputs.new('NodeSocketGeometry', 'Geometry')

# Link nodes
links.new(group_input.outputs['Geometry'], distribute_points.inputs['Mesh'])
links.new(distribute_points.outputs['Points'], point_instance.inputs['Points'])
links.new(distribute_points.outputs['Points'], random_scale.inputs['Seed'])
links.new(distribute_points.outputs['Points'], random_rotation.inputs['Seed'])

# Instance the rock mesh
point_instance.inputs['Instance'].default_value = rock_base

links.new(random_rotation.outputs['Value'], rotate_instances.inputs['Rotation'])
links.new(random_scale.outputs['Value'], scale_instances.inputs['Scale'])

# Connect instance nodes
links.new(point_instance.outputs['Instances'], rotate_instances.inputs['Instances'])
links.new(rotate_instances.outputs['Instances'], scale_instances.inputs['Instances'])
links.new(scale_instances.outputs['Instances'], realize_instances.inputs['Geometry'])
links.new(realize_instances.outputs['Geometry'], group_output.inputs['Geometry'])

# Hide the rock base from viewport
rock_base.hide_set(True)
rock_base.hide_render = True

# Add material to rocks
material = bpy.data.materials.new(name="RockMaterial")
material.use_nodes = True
bsdf = material.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (0.4, 0.35, 0.3, 1.0)
bsdf.inputs['Roughness'].default_value = 0.8

ground.data.materials.append(material)

# Set viewport shading
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'SOLID'

print("Rock scattering scene created successfully")
