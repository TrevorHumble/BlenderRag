import bpy
import bmesh
from mathutils import Vector

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create ground plane
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"

# Create rough rock mesh (icosphere with displacement)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 5))
rock = bpy.context.active_object
rock.name = "RockTemplate"

# Add some noise to the rock by subdividing and moving vertices
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.subdivide(number_cuts=3)
bpy.ops.object.mode_set(mode='OBJECT')

bm = bmesh.new()
bm.from_mesh(rock.data)
import random
random.seed(42)
for vert in bm.verts:
    offset = Vector((random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15)))
    vert.co += offset
bm.to_mesh(rock.data)
bm.free()
rock.data.update()

# Hide the rock template
rock.hide_set(True)
rock.hide_render = True

# Select ground plane for modifier
bpy.context.view_layer.objects.active = ground
ground.select_set(True)

# Add geometry nodes modifier
geom_mod = ground.modifiers.new(name="RockScatter", type='GEOMETRY')

# Create new geometry node tree
node_tree = bpy.data.node_groups.new("RockScatterNodes", "GeometryNodeTree")
geom_mod.node_group = node_tree

# Get input and output nodes
tree_nodes = node_tree.nodes
tree_nodes.clear()
tree_links = node_tree.links

# Create Input node (Group Input)
input_node = tree_nodes.new("NodeGroupInput")
input_node.location = (-200, 0)

# Create Output node (Group Output)
output_node = tree_nodes.new("NodeGroupOutput")
output_node.location = (1000, 0)

# Create Distribute Points on Faces node
distribute_node = tree_nodes.new("GeometryNodeDistributePointsOnFaces")
distribute_node.location = (0, 0)
distribute_node.distribute_method = 'RANDOM'

# Create Instance on Points node
instance_node = tree_nodes.new("GeometryNodeInstanceOnPoints")
instance_node.location = (250, 0)

# Create Object Info node for the rock template
object_info_node = tree_nodes.new("GeometryNodeObjectInfo")
object_info_node.location = (0, -150)
object_info_node.inputs['Object'].default_value = rock

# Create Random Value node for rotation randomization (X axis)
random_rot_x = tree_nodes.new("FunctionNodeRandomValue")
random_rot_x.location = (250, -150)
random_rot_x.inputs['Min'].default_value = 0.0
random_rot_x.inputs['Max'].default_value = 6.28319  # 2*PI

# Create Random Value node for rotation randomization (Y axis)
random_rot_y = tree_nodes.new("FunctionNodeRandomValue")
random_rot_y.location = (250, -250)
random_rot_y.inputs['Min'].default_value = 0.0
random_rot_y.inputs['Max'].default_value = 6.28319

# Create Random Value node for rotation randomization (Z axis)
random_rot_z = tree_nodes.new("FunctionNodeRandomValue")
random_rot_z.location = (250, -350)
random_rot_z.inputs['Min'].default_value = 0.0
random_rot_z.inputs['Max'].default_value = 6.28319

# Create Rotate Instances node
rotate_node = tree_nodes.new("GeometryNodeRotateInstances")
rotate_node.location = (500, 0)

# Create Vector from XYZ to compose rotation vector
vec_xyz_node = tree_nodes.new("ShaderNodeCombineXYZ")
vec_xyz_node.location = (400, -200)

# Create Random Value node for scale randomization
random_scale = tree_nodes.new("FunctionNodeRandomValue")
random_scale.location = (500, -100)
random_scale.inputs['Min'].default_value = 0.6
random_scale.inputs['Max'].default_value = 1.4

# Create Scale Instances node
scale_node = tree_nodes.new("GeometryNodeScaleInstances")
scale_node.location = (700, 0)

# Make links
# Geometry flow: Input -> Distribute Points -> Instance -> Rotate -> Scale -> Output
tree_links.new(input_node.outputs['Geometry'], distribute_node.inputs['Mesh'])
tree_links.new(distribute_node.outputs['Points'], instance_node.inputs['Points'])
tree_links.new(object_info_node.outputs['Geometry'], instance_node.inputs['Instance'])
tree_links.new(instance_node.outputs['Instances'], rotate_node.inputs['Instances'])
tree_links.new(rotate_node.outputs['Instances'], scale_node.inputs['Instances'])
tree_links.new(scale_node.outputs['Instances'], output_node.inputs['Geometry'])

# Link rotation randomization
tree_links.new(random_rot_x.outputs['Value'], vec_xyz_node.inputs['X'])
tree_links.new(random_rot_y.outputs['Value'], vec_xyz_node.inputs['Y'])
tree_links.new(random_rot_z.outputs['Value'], vec_xyz_node.inputs['Z'])
tree_links.new(vec_xyz_node.outputs['Vector'], rotate_node.inputs['Rotation'])

# Link scale randomization
tree_links.new(random_scale.outputs['Value'], scale_node.inputs['Scale'])

# Set distribute density
distribute_node.inputs['Density'].default_value = 50.0

# Select and deselect for clean state
ground.select_set(False)
bpy.ops.object.select_all(action='DESELECT')
