import bpy
import math

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene

# Set render engine to EEVEE
scene.render.engine = 'BLENDER_EEVEE'

# Configure volumetrics for atmospheric effect
eevee = scene.eevee
eevee.volumetric_samples = 128
eevee.volumetric_start = 0.1
eevee.volumetric_end = 20.0
eevee.volumetric_tile_size = '4'

# Create floor
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
floor = bpy.context.active_object
floor.name = "Floor"

# Create floor material (dark concrete)
floor_mat = bpy.data.materials.new(name="FloorMaterial")
floor_mat.use_nodes = True
bsdf = floor_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs['Base Color'].default_value = (0.15, 0.15, 0.15, 1.0)
bsdf.inputs['Roughness'].default_value = 0.8
floor.data.materials.append(floor_mat)

# Create back wall
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, -5, 5), rotation=(math.pi/2, 0, 0))
back_wall = bpy.context.active_object
back_wall.name = "BackWall"

# Create back wall material (dark plaster)
wall_mat = bpy.data.materials.new(name="WallMaterial")
wall_mat.use_nodes = True
bsdf = wall_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs['Base Color'].default_value = (0.2, 0.18, 0.16, 1.0)
bsdf.inputs['Roughness'].default_value = 0.9
back_wall.data.materials.append(wall_mat)

# Create right wall
bpy.ops.mesh.primitive_plane_add(size=10, location=(5, 0, 5), rotation=(math.pi/2, 0, math.pi/2))
right_wall = bpy.context.active_object
right_wall.name = "RightWall"
right_wall.data.materials.append(wall_mat)

# Create window frame (opening in back wall)
bpy.ops.mesh.primitive_plane_add(size=2, location=(0, -4.9, 5), rotation=(math.pi/2, 0, 0))
window_frame = bpy.context.active_object
window_frame.name = "WindowFrame"

# Create window material (semi-transparent glass)
window_mat = bpy.data.materials.new(name="WindowMaterial")
window_mat.use_nodes = True
bsdf = window_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs['Base Color'].default_value = (0.7, 0.8, 0.9, 1.0)
bsdf.inputs['Transmission Weight'].default_value = 0.8
bsdf.inputs['Roughness'].default_value = 0.05
window_frame.data.materials.append(window_mat)

# Create emissive lamp (wall-mounted)
bpy.ops.object.light_add(type='AREA', radius=0.5, location=(3, -3, 6))
lamp = bpy.context.active_object
lamp.name = "EmissiveLamp"
lamp.data.energy = 150
lamp.data.size = 0.3

# Create lamp material with emission
lamp_mat = bpy.data.materials.new(name="LampEmission")
lamp_mat.use_nodes = True
nodes = lamp_mat.node_tree.nodes
nodes.clear()
node_emission = nodes.new(type='ShaderNodeEmission')
node_output = nodes.new(type='ShaderNodeOutputMaterial')
node_emission.inputs['Color'].default_value = (0.95, 0.85, 0.6, 1.0)
node_emission.inputs['Strength'].default_value = 3.0
lamp_mat.node_tree.links.new(node_emission.outputs['Emission'], node_output.inputs['Surface'])

# Create world shader with volumetric absorption
world = bpy.data.worlds["World"]
world.use_nodes = True
world_nodes = world.node_tree.nodes
world_nodes.clear()

# Add background shader
bg_node = world_nodes.new(type='ShaderNodeBackground')
bg_node.inputs['Color'].default_value = (0.1, 0.1, 0.12, 1.0)
bg_node.inputs['Strength'].default_value = 0.5

# Add world output
world_output = world_nodes.new(type='ShaderNodeOutputWorld')
world.node_tree.links.new(bg_node.outputs['Background'], world_output.inputs['Surface'])

# Create volume shader for atmospheric effect
world_volume = world_nodes.new(type='ShaderNodeVolumePrincipled')
world_volume.inputs['Density'].default_value = 0.01
world_volume.inputs['Anisotropy'].default_value = 0.5

# Link volume to world output
world.node_tree.links.new(world_volume.outputs['Volume'], world_output.inputs['Volume'])

# Set up camera
bpy.ops.object.camera_add(location=(7, 7, 4))
camera = bpy.context.active_object
camera.name = "Camera"
scene.camera = camera

# Configure render for moody look
scene.render.samples = 128
scene.render.use_motion_blur = False

print("Moody interior corner scene created successfully!")
