import bpy
import bmesh
from mathutils import Vector

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create a plane (ground)
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
plane = bpy.context.active_object
plane.name = "Ground"

# Create a UV sphere to use as the rock base geometry
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 5))
rock_base = bpy.context.active_object
rock_base.name = "RockBase"

# Add some roughness to the rock using a remesh modifier to make it less smooth
bpy.ops.object.modifier_add(type='REMESH')
remesh_mod = rock_base.modifiers['Remesh']
remesh_mod.voxel_size = 0.15
remesh_mod.use_smooth_shade = True

# Hide the rock base from view (will be instanced)
rock_base.hide_set(True)

# Create a geometry node tree
gn_tree = bpy.data.node_groups.new(name="RockScatter", type='GEOMETRY')

# Clear default nodes
gn_tree.nodes.clear()

# Create socket links
gn_tree.links.clear()

# Add Group Input and Output nodes
group_input = gn_tree.nodes.new(type='NodeGroupInput')
group_output = gn_tree.nodes.new(type='NodeGroupOutput')

# Position them
group_input.location = (-400, 0)
group_output.location = (800, 0)

# Add Distribute Points on Faces node
dist_points = gn_tree.nodes.new(type='GeometryNodeDistributePointsOnFaces')
dist_points.location = (-200, 100)
dist_points.inputs['Density'].default_value = 50.0

# Add Instance on Points node
instance_node = gn_tree.nodes.new(type='GeometryNodeInstanceOnPoints')
instance_node.location = (100, 100)

# Add Random Value node for scale randomization
random_scale = gn_tree.nodes.new(type='GeometryNodeRandomValue')
random_scale.location = (-200, -150)
random_scale.inputs['Min'].default_value = 0.6
random_scale.inputs['Max'].default_value = 1.4
random_scale.data_type = 'FLOAT'

# Add Scale Instances node
scale_inst = gn_tree.nodes.new(type='GeometryNodeScaleInstances')
scale_inst.location = (300, 100)

# Add Random Value node for rotation randomization
random_rotation = gn_tree.nodes.new(type='GeometryNodeRandomValue')
random_rotation.location = (100, -150)
random_rotation.inputs['Min'].default_value = (0.0, 0.0, 0.0)
random_rotation.inputs['Max'].default_value = (6.28, 6.28, 6.28)
random_rotation.data_type = 'FLOAT_VECTOR'

# Add Rotate Instances node
rotate_inst = gn_tree.nodes.new(type='GeometryNodeRotateInstances')
rotate_inst.location = (500, 100)
rotate_inst.inputs['Type'].default_value = 'EULER'

# Connect nodes
gn_tree.links.new(group_input.outputs['Geometry'], dist_points.inputs['Mesh'])
gn_tree.links.new(dist_points.outputs['Points'], instance_node.inputs['Points'])
gn_tree.links.new(group_input.outputs['Geometry'], instance_node.inputs['Instance'])

# Connect to scale node
gn_tree.links.new(instance_node.outputs['Instances'], scale_inst.inputs['Instances'])
gn_tree.links.new(random_scale.outputs['Value'], scale_inst.inputs['Scale'])

# Connect to rotate node
gn_tree.links.new(scale_inst.outputs['Instances'], rotate_inst.inputs['Instances'])
gn_tree.links.new(random_rotation.outputs['Value'], rotate_inst.inputs['Rotation'])

# Connect output
gn_tree.links.new(rotate_inst.outputs['Instances'], group_output.inputs['Geometry'])

# Select plane and add geometry nodes modifier
bpy.context.view_layer.objects.active = plane
plane.select_set(True)

# Add modifier with the geometry node tree
mod = plane.modifiers.new(name="RockScatter", type='GEOMETRY')
mod.node_group = gn_tree

# Make the plane the input to the group
# The plane geometry will be available as the group's input Geometry
# This is handled automatically when the modifier is applied

# Switch to object shading mode to see results
for area in bpy.context.screen.areas:
    if area.type == 'PROPERTIES':
        for space in area.spaces:
            if space.type == 'PROPERTIES':
                space.context = 'MODIFIER'

# Set viewport shading to solid with better visibility
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'SOLID'

# Frame all
bpy.ops.view3d.view_all()

print("Procedural rock scatter created successfully on ground plane with randomized scale and rotation")
