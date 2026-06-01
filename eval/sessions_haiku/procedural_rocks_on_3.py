import bpy
import bmesh
from mathutils import Vector

# Clear the scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create a plane for the ground
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"

# Create a rough rock mesh (icosphere with displacements)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 0))
rock = bpy.context.active_object
rock.name = "Rock"

# Add some roughness to the rock by adding a subdivision surface and displacing vertices
me = rock.data
bm = bmesh.new()
bm.from_mesh(me)

# Subdivide the mesh a couple of times for detail
bmesh.ops.subdivide_edges(bm, edges=bm.edges, number_cuts=2)
bm.to_mesh(me)
bm.free()

# Add a displace modifier for roughness (use noise texture)
displace_mod = rock.modifiers.new(name="Displace", type='DISPLACE')

# Create a texture for displacement
tex = bpy.data.textures.new(name="RockNoise", type='CLOUDS')
tex.cloud_type = 'COLOR'
tex.scale = 0.5
displace_mod.texture = tex
displace_mod.strength = 0.15

# Hide the rock from view; it will only exist as a reference
rock.hide_set(True)
rock.hide_render = True

# Add a geometry nodes modifier to the ground plane
geo_mod = ground.modifiers.new(name="RockScatter", type='GEOMETRY')

# Create a new node tree
node_tree = bpy.data.node_groups.new(name="RockScatterTree", type='GEOMETRY')
geo_mod.node_group = node_tree

# Clear default nodes
node_tree.nodes.clear()

# Create input/output nodes
group_input = node_tree.nodes.new(type='NodeGroupInput')
group_output = node_tree.nodes.new(type='NodeGroupOutput')

# Layout X positions for organization
x_pos = 0
node_width = 200

# --- Distribute Points on Faces ---
x_pos += node_width
distribute_points = node_tree.nodes.new(type='GeometryNodeDistributePointsOnFaces')
distribute_points.location = (x_pos, 200)
distribute_points.distribute_method = 'POISSON'
distribute_points.inputs['Density'].default_value = 0.5

# --- Create Rock Reference (Geometry to Instance) ---
x_pos += node_width
geo_to_instance = node_tree.nodes.new(type='GeometryNodeGeometryToInstance')
geo_to_instance.location = (x_pos, 100)

# --- Instance on Points ---
x_pos += node_width
instance_on_points = node_tree.nodes.new(type='GeometryNodeInstanceOnPoints')
instance_on_points.location = (x_pos, 200)

# --- Random Value for Rotation (X) ---
x_pos_random_x = x_pos
random_rotation_x = node_tree.nodes.new(type='FunctionNodeRandomValue')
random_rotation_x.location = (x_pos_random_x - 100, 400)
random_rotation_x.data_type = 'FLOAT_VECTOR'
random_rotation_x.inputs['Min'].default_value = (0, 0, 0)
random_rotation_x.inputs['Max'].default_value = (6.28, 0, 0)

# --- Random Value for Rotation (Y) ---
random_rotation_y = node_tree.nodes.new(type='FunctionNodeRandomValue')
random_rotation_y.location = (x_pos_random_x - 100, 300)
random_rotation_y.data_type = 'FLOAT_VECTOR'
random_rotation_y.inputs['Min'].default_value = (0, 0, 0)
random_rotation_y.inputs['Max'].default_value = (0, 6.28, 0)

# --- Random Value for Rotation (Z) ---
random_rotation_z = node_tree.nodes.new(type='FunctionNodeRandomValue')
random_rotation_z.location = (x_pos_random_x - 100, 200)
random_rotation_z.data_type = 'FLOAT_VECTOR'
random_rotation_z.inputs['Min'].default_value = (0, 0, 0)
random_rotation_z.inputs['Max'].default_value = (0, 0, 6.28)

# --- Combine Rotation Values ---
x_pos += node_width
combine_xyz_rot = node_tree.nodes.new(type='ShaderNodeCombineXYZ')
combine_xyz_rot.location = (x_pos_random_x + 50, 300)

# Extract individual components from random vectors
separate_x = node_tree.nodes.new(type='ShaderNodeSeparateXYZ')
separate_x.location = (x_pos_random_x + 50, 400)

separate_y = node_tree.nodes.new(type='ShaderNodeSeparateXYZ')
separate_y.location = (x_pos_random_x + 50, 300)

separate_z = node_tree.nodes.new(type='ShaderNodeSeparateXYZ')
separate_z.location = (x_pos_random_x + 50, 200)

# --- Rotate Instances ---
x_pos += node_width * 2
rotate_instances = node_tree.nodes.new(type='GeometryNodeRotateInstances')
rotate_instances.location = (x_pos, 200)
rotate_instances.rotation_type = 'EULER'

# --- Random Value for Scale ---
random_scale = node_tree.nodes.new(type='FunctionNodeRandomValue')
random_scale.location = (x_pos - 100, 50)
random_scale.data_type = 'FLOAT'
random_scale.inputs['Min'].default_value = 0.6
random_scale.inputs['Max'].default_value = 1.4

# --- Scale Instances ---
x_pos += node_width
scale_instances = node_tree.nodes.new(type='GeometryNodeScaleInstances')
scale_instances.location = (x_pos, 200)

# --- Connect Nodes ---
# Input geometry to distribute points
node_tree.links.new(group_input.outputs['Geometry'], distribute_points.inputs['Mesh'])

# Rock reference setup
node_tree.links.new(geo_to_instance.outputs['Instance'], instance_on_points.inputs['Instance'])
instance_on_points.inputs['Instance'].default_value = rock

# Points from distribute to instance on points
node_tree.links.new(distribute_points.outputs['Points'], instance_on_points.inputs['Points'])

# Instance to rotate
node_tree.links.new(instance_on_points.outputs['Instances'], rotate_instances.inputs['Instances'])

# Random rotation values
node_tree.links.new(random_rotation_x.outputs['Value'], separate_x.inputs['Vector'])
node_tree.links.new(random_rotation_y.outputs['Value'], separate_y.inputs['Vector'])
node_tree.links.new(random_rotation_z.outputs['Value'], separate_z.inputs['Vector'])

# Combine rotation components
node_tree.links.new(separate_x.outputs['X'], combine_xyz_rot.inputs['X'])
node_tree.links.new(separate_y.outputs['Y'], combine_xyz_rot.inputs['Y'])
node_tree.links.new(separate_z.outputs['Z'], combine_xyz_rot.inputs['Z'])

# Apply rotation
node_tree.links.new(combine_xyz_rot.outputs['Vector'], rotate_instances.inputs['Rotation'])

# Scale instances
node_tree.links.new(rotate_instances.outputs['Instances'], scale_instances.inputs['Instances'])
node_tree.links.new(random_scale.outputs['Value'], scale_instances.inputs['Scale'])

# Output
node_tree.links.new(scale_instances.outputs['Instances'], group_output.inputs['Geometry'])

# Select ground for viewport visibility
bpy.context.view_layer.objects.active = ground
ground.select_set(True)
