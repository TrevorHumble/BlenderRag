import bpy
import math
from mathutils import Vector

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

world = bpy.data.worlds["World"]
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[1].default_value = 0.3

scene = bpy.context.scene
scene.eevee.use_volumetric_shadows = True
scene.eevee.volumetric_tile_size = '8x8'
scene.eevee.volumetric_samples = 64
scene.eevee.volumetric_shadow_samples = 16

bpy.ops.mesh.primitive_cube_add(size=0.1, location=(0, 0, -0.05))
floor = bpy.context.active_object
floor.scale = (4, 4, 0.1)
floor.location = (0, 0, -0.05)
bpy.ops.object.transform_apply(scale=True)

floor_mat = bpy.data.materials.new(name="FloorMaterial")
floor_mat.use_nodes = True
floor_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.15, 0.15, 0.15, 1.0)
floor_mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.7
floor.data.materials.append(floor_mat)

bpy.ops.mesh.primitive_cube_add(size=1, location=(-2, 0, 1))
wall1 = bpy.context.active_object
wall1.scale = (0.1, 4, 2)
wall1.location = (-2, 0, 1)
bpy.ops.object.transform_apply(scale=True)

wall_mat = bpy.data.materials.new(name="WallMaterial")
wall_mat.use_nodes = True
wall_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2, 0.18, 0.16, 1.0)
wall_mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
wall1.data.materials.append(wall_mat)

bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 2, 1))
wall2 = bpy.context.active_object
wall2.scale = (4, 0.1, 2)
wall2.location = (0, 2, 1)
bpy.ops.object.transform_apply(scale=True)
wall2.data.materials.append(wall_mat)

bpy.ops.mesh.primitive_cube_add(size=0.5, location=(2.5, 1.2, 1.2))
window_frame = bpy.context.active_object
window_frame.scale = (0.8, 1.0, 1.0)
window_frame.location = (2.5, 1.2, 1.2)
bpy.ops.object.transform_apply(scale=True)

frame_mat = bpy.data.materials.new(name="FrameMaterial")
frame_mat.use_nodes = True
frame_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.1, 0.1, 0.1, 1.0)
frame_mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.3
window_frame.data.materials.append(frame_mat)

bpy.ops.mesh.primitive_plane_add(size=0.4, location=(2.5, 1.2, 1.2))
window_pane = bpy.context.active_object
window_pane.scale = (0.7, 0.9, 0.05)
window_pane.location = (2.5, 1.2, 1.2)
bpy.ops.object.transform_apply(scale=True)

glass_mat = bpy.data.materials.new(name="GlassMaterial")
glass_mat.use_nodes = True
glass_node_tree = glass_mat.node_tree
bsdf = glass_node_tree.nodes["Principled BSDF"]
bsdf.inputs["Transmission"].default_value = 1.0
bsdf.inputs["IOR"].default_value = 1.45
bsdf.inputs["Roughness"].default_value = 0.05
bsdf.inputs["Base Color"].default_value = (0.9, 0.95, 1.0, 1.0)
window_pane.data.materials.append(glass_mat)

bpy.ops.object.light_add(type='SUN', location=(3, -2, 3))
sun = bpy.context.active_object
sun.data.energy = 800
sun.data.angle = math.radians(5)
sun.rotation_euler = (math.radians(50), math.radians(-40), 0)

bpy.ops.object.light_add(type='POINT', location=(0.5, 0.5, 1.5))
lamp = bpy.context.active_object
lamp.data.energy = 150
lamp_mat = bpy.data.materials.new(name="LampEmissive")
lamp_mat.use_nodes = True
lamp_bsdf = lamp_mat.node_tree.nodes["Principled BSDF"]
lamp_bsdf.inputs["Base Color"].default_value = (1.0, 0.95, 0.85, 1.0)
lamp_bsdf.inputs["Emission"].default_value = (1.0, 0.95, 0.85, 1.0)
lamp_bsdf.inputs["Emission Strength"].default_value = 3.0

bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(0.5, 0.5, 1.5))
lamp_bulb = bpy.context.active_object
lamp_bulb.data.materials.append(lamp_mat)

density_obj = bpy.data.objects.new("VolumetricsVolume", bpy.data.meshes.new("VolumeMesh"))
bpy.context.collection.objects.link(density_obj)
bpy.context.view_layer.objects.active = density_obj

bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.mesh.primitive_cube_add(size=5, location=(0, 0, 1.5))
volume_cube = bpy.context.active_object
volume_mat = bpy.data.materials.new(name="VolumeMaterial")
volume_mat.use_nodes = True
volume_mat.volume_render_method = 'SINGLE_SCATTERING'
volume_node_tree = volume_mat.node_tree
volume_node_tree.nodes.clear()
volume_out = volume_node_tree.nodes.new(type='ShaderNodeOutputMaterial')
volume_principled = volume_node_tree.nodes.new(type='ShaderNodeVolumePrincipled')
volume_node_tree.links.new(volume_principled.outputs['Volume'], volume_out.inputs['Volume'])
volume_principled.inputs["Density"].default_value = 0.15
volume_principled.inputs["Anisotropy"].default_value = 0.5
volume_cube.data.materials.append(volume_mat)

bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
bpy.context.scene.eevee.use_bloom = True
bpy.context.scene.eevee.bloom_intensity = 0.5

bpy.context.scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.08, 1.0)

for obj in bpy.context.scene.objects:
    obj.select_set(False)

bpy.context.view_layer.objects.active = None
