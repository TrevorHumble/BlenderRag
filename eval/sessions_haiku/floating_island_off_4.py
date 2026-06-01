import bpy
import bmesh
import math
from mathutils import Vector

# Clear the default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Set world background to light blue/gray daylight
world = bpy.data.worlds["World"]
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.85, 0.9, 1.0, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.2

# Add sun light for daylight
sun = bpy.data.objects.new("Sun", bpy.data.lights.new(name="SunLight", type='SUN'))
bpy.context.collection.objects.link(sun)
sun.data.energy = 3.0
sun.data.angle = math.radians(15)
sun.location = (5, 5, 10)
sun.rotation_euler = (math.radians(45), math.radians(45), 0)

# Create rocky base - a rocky icosphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=2.5, location=(0, 0, 0))
base = bpy.context.active_object
base.name = "RockyBase"
base.data.name = "RockyBaseMesh"

# Subdivide the sphere for more detail
bpy.context.view_layer.objects.active = base
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.subdivide(number_cuts=2)
bpy.ops.object.mode_set(mode='OBJECT')

# Add a displace modifier to make it rocky
displace = base.modifiers.new(name="RockyDisplace", type='DISPLACE')
displace.strength = 0.4

# Add a noise texture for the rocky look
noise_tex = bpy.data.textures.new(name="RockNoise", type='CLOUDS')
noise_tex.cloud_type = 'COLOR'
displace.texture = noise_tex

# Create a brown rocky material
rock_mat = bpy.data.materials.new(name="RockMaterial")
rock_mat.use_nodes = True
rock_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.5, 0.4, 0.35, 1.0)
rock_mat.node_tree.nodes["Principled BSDF"].inputs[9].default_value = 0.8
base.data.materials.append(rock_mat)

# Create grass layer on top - a low-poly plane with subdivision
bpy.ops.mesh.primitive_plane_add(size=5, location=(0, 0, 2.5))
grass_base = bpy.context.active_object
grass_base.name = "GrassTop"
grass_base.data.name = "GrassTopMesh"

# Subdivide grass plane for detail
bpy.context.view_layer.objects.active = grass_base
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.subdivide(number_cuts=3)
bpy.ops.object.mode_set(mode='OBJECT')

# Add slight height variation to grass
displace_grass = grass_base.modifiers.new(name="GrassDisplace", type='DISPLACE')
displace_grass.strength = 0.15
grass_noise = bpy.data.textures.new(name="GrassNoise", type='CLOUDS')
grass_noise.cloud_type = 'COLOR'
displace_grass.texture = grass_noise

# Create green grass material
grass_mat = bpy.data.materials.new(name="GrassMaterial")
grass_mat.use_nodes = True
grass_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.2, 0.6, 0.3, 1.0)
grass_mat.node_tree.nodes["Principled BSDF"].inputs[9].default_value = 0.4
grass_base.data.materials.append(grass_mat)

# Create first tree - cone for body, small sphere for top
tree1_body = bpy.data.objects.new("Tree1Body", bpy.data.meshes.new("Tree1BodyMesh"))
bpy.context.collection.objects.link(tree1_body)
bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.4, radius2=0.1, depth=2.0, location=(-1.5, -1.0, 3.5))
tree1_body = bpy.context.active_object
tree1_body.name = "Tree1Body"

# Add wood material
wood_mat = bpy.data.materials.new(name="WoodMaterial")
wood_mat.use_nodes = True
wood_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.4, 0.3, 0.2, 1.0)
tree1_body.data.materials.append(wood_mat)

# Add foliage as a sphere on top
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.7, location=(-1.5, -1.0, 4.8))
tree1_foliage = bpy.context.active_object
tree1_foliage.name = "Tree1Foliage"

# Add foliage material
foliage_mat = bpy.data.materials.new(name="FoliageMaterial")
foliage_mat.use_nodes = True
foliage_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.25, 0.5, 0.2, 1.0)
foliage_mat.node_tree.nodes["Principled BSDF"].inputs[9].default_value = 0.6
tree1_foliage.data.materials.append(foliage_mat)

# Create second tree offset
bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.35, radius2=0.08, depth=1.8, location=(1.2, 1.5, 3.5))
tree2_body = bpy.context.active_object
tree2_body.name = "Tree2Body"
tree2_body.data.materials.append(wood_mat)

bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(1.2, 1.5, 4.7))
tree2_foliage = bpy.context.active_object
tree2_foliage.name = "Tree2Foliage"
tree2_foliage.data.materials.append(foliage_mat)

# Set render engine to Eevee and apply AgX view transform
bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.context.scene.display_settings.view_transform = 'AgX'

# Set render resolution
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080

# Deselect all objects and frame the view
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        obj.select_set(True)
bpy.ops.view3d.view_all()
