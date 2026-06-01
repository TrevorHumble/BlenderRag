import bpy
import math
from mathutils import Vector

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create floor plane
floor_mesh = bpy.data.meshes.new("Floor")
floor_obj = bpy.data.objects.new("Floor", floor_mesh)
bpy.context.collection.objects.link(floor_obj)
bpy.context.view_layer.objects.active = floor_obj
floor_obj.select_set(True)

# Create floor geometry
bm = bpy.bmesh.new()
bm.verts.new((0, 0, 0))
bm.verts.new((10, 0, 0))
bm.verts.new((10, 10, 0))
bm.verts.new((0, 10, 0))
bm.faces.new(bm.verts[:])
bm.to_mesh(floor_mesh)
bm.free()

# Create first wall (vertical, along X)
wall1_mesh = bpy.data.meshes.new("Wall1")
wall1_obj = bpy.data.objects.new("Wall1", wall1_mesh)
bpy.context.collection.objects.link(wall1_obj)

bm = bpy.bmesh.new()
bm.verts.new((0, 0, 0))
bm.verts.new((10, 0, 0))
bm.verts.new((10, 0, 3))
bm.verts.new((0, 0, 3))
bm.faces.new(bm.verts[:])
bm.to_mesh(wall1_mesh)
bm.free()

# Create second wall (vertical, along Y)
wall2_mesh = bpy.data.meshes.new("Wall2")
wall2_obj = bpy.data.objects.new("Wall2", wall2_mesh)
bpy.context.collection.objects.link(wall2_obj)

bm = bpy.bmesh.new()
bm.verts.new((0, 0, 0))
bm.verts.new((0, 10, 0))
bm.verts.new((0, 10, 3))
bm.verts.new((0, 0, 3))
bm.faces.new(bm.verts[:])
bm.to_mesh(wall2_mesh)
bm.free()

# Create window frame (simple quad)
window_mesh = bpy.data.meshes.new("Window")
window_obj = bpy.data.objects.new("Window", window_mesh)
bpy.context.collection.objects.link(window_obj)
window_obj.location = (0, 3, 1.5)

bm = bpy.bmesh.new()
bm.verts.new((0, 0, 0))
bm.verts.new((0, 2, 0))
bm.verts.new((0, 2, 1.5))
bm.verts.new((0, 0, 1.5))
bm.faces.new(bm.verts[:])
bm.to_mesh(window_mesh)
bm.free()

# Create sun lamp for window light
sun_lamp = bpy.data.lights.new(name="SunLight", type='SUN')
sun_lamp.energy = 2.0
sun_obj = bpy.data.objects.new("SunLight", sun_lamp)
bpy.context.collection.objects.link(sun_obj)
sun_obj.location = (2, 5, 4)
sun_obj.rotation_euler = (math.radians(45), math.radians(45), 0)

# Create emissive lamp in corner
lamp_mesh = bpy.data.meshes.new("LampBulb")
lamp_obj = bpy.data.objects.new("LampBulb", lamp_mesh)
bpy.context.collection.objects.link(lamp_obj)
lamp_obj.location = (1, 1, 2.5)

# Create simple sphere for lamp
bm = bpy.bmesh.new()
for i in range(16):
    theta = (i / 16.0) * 2 * math.pi
    for j in range(8):
        phi = (j / 8.0) * math.pi
        x = 0.2 * math.sin(phi) * math.cos(theta)
        y = 0.2 * math.sin(phi) * math.sin(theta)
        z = 0.2 * math.cos(phi)
        bm.verts.new((x, y, z))

bm.to_mesh(lamp_mesh)
bm.free()

# Add emissive material to lamp
lamp_mat = bpy.data.materials.new(name="LampEmissive")
lamp_mat.use_nodes = True
lamp_mat.node_tree.nodes["Principled BSDF"].inputs["Emission"].default_value = (1.0, 0.9, 0.7, 1.0)
lamp_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 5.0
lamp_obj.data.materials.append(lamp_mat)

# Switch to EEVEE Next for volumetrics
if bpy.context.scene.render.engine != 'BLENDER_EEVEE_NEXT':
    bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'

# Set world to dark for moody atmosphere
world = bpy.context.scene.world
world.use_nodes = True
bg_node = world.node_tree.nodes["Background"]
bg_node.inputs["Background"].default_value = (0.02, 0.02, 0.05, 1.0)

# Add volume scatter for atmospheric effect
volume_mesh = bpy.data.meshes.new("VolumeScatter")
volume_obj = bpy.data.objects.new("VolumeScatter", volume_mesh)
bpy.context.collection.objects.link(volume_obj)

# Create volume boundary box
bm = bpy.bmesh.new()
bm.verts.new((0, 0, 0))
bm.verts.new((10, 0, 0))
bm.verts.new((10, 10, 0))
bm.verts.new((0, 10, 0))
bm.verts.new((0, 0, 3))
bm.verts.new((10, 0, 3))
bm.verts.new((10, 10, 3))
bm.verts.new((0, 10, 3))

# Create cube faces
verts = bm.verts[:]
bm.faces.new([verts[0], verts[1], verts[5], verts[4]])
bm.faces.new([verts[2], verts[3], verts[7], verts[6]])
bm.faces.new([verts[0], verts[3], verts[7], verts[4]])
bm.faces.new([verts[1], verts[2], verts[6], verts[5]])

bm.to_mesh(volume_mesh)
bm.free()

# Add volume material
volume_mat = bpy.data.materials.new(name="VolumeScatter")
volume_mat.use_nodes = True
volume_mat.node_tree.nodes.clear()

# Create volume scatter shader
bsdf = volume_mat.node_tree.nodes.new(type='ShaderNodeVolumeScatter')
bsdf.inputs["Density"].default_value = 0.1
bsdf.inputs["Anisotropy"].default_value = 0.0
link = volume_mat.node_tree.links.new(bsdf.outputs["Volume"], volume_mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial').inputs["Volume"])

volume_obj.data.materials.append(volume_mat)

# Add materials to walls and floor
floor_mat = bpy.data.materials.new(name="FloorMaterial")
floor_mat.use_nodes = True
floor_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.1, 0.1, 0.12, 1.0)
floor_obj.data.materials.append(floor_mat)

wall_mat = bpy.data.materials.new(name="WallMaterial")
wall_mat.use_nodes = True
wall_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.15, 0.15, 0.18, 1.0)
wall1_obj.data.materials.append(wall_mat)
wall2_obj.data.materials.append(wall_mat)

# Add material to window
window_mat = bpy.data.materials.new(name="WindowGlass")
window_mat.use_nodes = True
principled = window_mat.node_tree.nodes["Principled BSDF"]
principled.inputs["Base Color"].default_value = (0.7, 0.9, 1.0, 1.0)
principled.inputs["Transmission"].default_value = 1.0
principled.inputs["IOR"].default_value = 1.45
window_obj.data.materials.append(window_mat)

# Set viewport to rendered view
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading_type = 'MATERIAL'

print("Moody interior scene created successfully")
