import bpy
import bmesh
from mathutils import Vector

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create world background
world = bpy.data.worlds['World']
world.use_nodes = True
bg_node = world.node_tree.nodes['Background']
bg_node.inputs['Strength'].default_value = 0.8
bg_node.inputs['Color'].default_value = (0.05, 0.05, 0.08, 1.0)

# Add volume scatter to world
volume_node = world.node_tree.nodes.new('ShaderNodeVolumeScatter')
volume_node.inputs['Density'].default_value = 0.02
volume_node.inputs['Color'].default_value = (0.7, 0.7, 0.8, 1.0)
world.node_tree.links.new(volume_node.outputs['Volume'], world.node_tree.nodes['World Output'].inputs['Volume'])

# Create floor
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
floor = bpy.context.active_object
floor.name = "Floor"
floor_mat = bpy.data.materials.new(name="FloorMat")
floor_mat.use_nodes = True
floor_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.15, 0.13, 0.12, 1.0)
floor_mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.8
floor.data.materials.append(floor_mat)

# Create back wall
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 5, 5))
back_wall = bpy.context.active_object
back_wall.name = "BackWall"
back_wall.rotation_euler = (1.5708, 0, 0)
wall_mat = bpy.data.materials.new(name="WallMat")
wall_mat.use_nodes = True
wall_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.2, 0.18, 0.16, 1.0)
wall_mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.7
back_wall.data.materials.append(wall_mat)

# Create right wall
bpy.ops.mesh.primitive_plane_add(size=10, location=(5, 0, 5))
right_wall = bpy.context.active_object
right_wall.name = "RightWall"
right_wall.rotation_euler = (0, 1.5708, 0)
right_wall.data.materials.append(wall_mat)

# Create window frame (simple plane with emission for light)
bpy.ops.mesh.primitive_plane_add(size=2, location=(5, 2, 6))
window = bpy.context.active_object
window.name = "Window"
window.rotation_euler = (0, 1.5708, 0)
window_mat = bpy.data.materials.new(name="WindowMat")
window_mat.use_nodes = True
window_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.9, 0.95, 1.0, 1.0)
window_mat.node_tree.nodes['Principled BSDF'].inputs['Emission'].default_value = (0.8, 0.85, 1.0, 1.0)
window_mat.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 2.0
window.data.materials.append(window_mat)

# Create lamp (emissive sphere)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(2, 1, 2.5))
lamp = bpy.context.active_object
lamp.name = "Lamp"
lamp_mat = bpy.data.materials.new(name="LampMat")
lamp_mat.use_nodes = True
lamp_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (1.0, 0.9, 0.7, 1.0)
lamp_mat.node_tree.nodes['Principled BSDF'].inputs['Emission'].default_value = (1.0, 0.9, 0.7, 1.0)
lamp_mat.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 3.0
lamp.data.materials.append(lamp_mat)

# Set render engine to Eevee Next for volumetrics
bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'

# Add volume density to scene
bpy.context.scene.eevee.volumetric_start = 0.1
bpy.context.scene.eevee.volumetric_end = 50.0
bpy.context.scene.eevee.volumetric_sampling_distribution = 0.5

# Set up camera
bpy.ops.object.camera_add(location=(8, -8, 4))
camera = bpy.context.active_object
camera.name = "Camera"
bpy.context.scene.camera = camera

# Set up lighting
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
