import bpy
import bmesh
import random
from mathutils import Vector

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create rocky base (icosphere with displacement for rough texture)
bpy.ops.mesh.primitive_uv_sphere_add(radius=3, location=(0, 0, 0))
base_obj = bpy.context.active_object
base_obj.name = "RockyBase"

# Add subdivision surface for detail
subsurf = base_obj.modifiers.new(name="Subdivision", type='SUBSURF')
subsurf.levels = 2
subsurf.render_levels = 3

# Add some noise displacement for rocky appearance
base_obj.data.use_auto_smooth = True

# Create grass platform (cylinder, flat top)
bpy.ops.mesh.primitive_cylinder_add(radius=3.2, depth=0.8, location=(0, 0, 2.5))
grass_base = bpy.context.active_object
grass_base.name = "GrassBase"

# Flatten and position to sit on top of rocky base
bpy.ops.object.shade_smooth()

# Add grass material
grass_mat = bpy.data.materials.new(name="GrassMaterial")
grass_mat.use_nodes = True
bsdf = grass_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.2, 0.6, 0.2, 1.0)  # Green
bsdf.inputs["Roughness"].default_value = 0.7

grass_base.data.materials.append(grass_mat)

# Add rock material to base
rock_mat = bpy.data.materials.new(name="RockMaterial")
rock_mat.use_nodes = True
bsdf_rock = rock_mat.node_tree.nodes["Principled BSDF"]
bsdf_rock.inputs["Base Color"].default_value = (0.4, 0.4, 0.42, 1.0)  # Gray rock
bsdf_rock.inputs["Roughness"].default_value = 0.85

base_obj.data.materials.append(rock_mat)

# Create first low-poly tree (cone trunk + sphere foliage)
# Trunk
bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=1.0, location=(-1.2, 0, 3.5))
trunk1 = bpy.context.active_object
trunk1.name = "Tree1Trunk"

# Tree foliage (sphere)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(-1.2, 0, 4.3))
foliage1 = bpy.context.active_object
foliage1.name = "Tree1Foliage"

# Add tree material (brown trunk, green foliage)
trunk_mat = bpy.data.materials.new(name="TrunkMaterial")
trunk_mat.use_nodes = True
bsdf_trunk = trunk_mat.node_tree.nodes["Principled BSDF"]
bsdf_trunk.inputs["Base Color"].default_value = (0.35, 0.2, 0.1, 1.0)  # Brown
bsdf_trunk.inputs["Roughness"].default_value = 0.8

trunk1.data.materials.append(trunk_mat)

foliage_mat = bpy.data.materials.new(name="FoliageMaterial")
foliage_mat.use_nodes = True
bsdf_foliage = foliage_mat.node_tree.nodes["Principled BSDF"]
bsdf_foliage.inputs["Base Color"].default_value = (0.15, 0.45, 0.1, 1.0)  # Dark green
bsdf_foliage.inputs["Roughness"].default_value = 0.6

foliage1.data.materials.append(foliage_mat)

# Create second low-poly tree (offset position)
bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.9, location=(1.5, -0.8, 3.5))
trunk2 = bpy.context.active_object
trunk2.name = "Tree2Trunk"
trunk2.data.materials.append(trunk_mat)

bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55, location=(1.5, -0.8, 4.2))
foliage2 = bpy.context.active_object
foliage2.name = "Tree2Foliage"
foliage2.data.materials.append(foliage_mat)

# Set up lighting - soft daylight
bpy.ops.object.light_add(type='SUN', location=(5, 5, 8))
sun = bpy.context.active_object
sun.name = "DayLight"
sun.data.energy = 2.0
sun.data.angle = 0.5

# Add HDRI-like world lighting for softness
world = bpy.context.scene.world
world.use_nodes = True
bg_node = world.node_tree.nodes["Background"]
bg_node.inputs["Background"].default_value = (0.7, 0.75, 0.8, 1.0)  # Light blue sky
bg_node.inputs["Strength"].default_value = 0.8

# Set render engine to EEVEE and configure view transform
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'

# Set view_transform to AgX (correct casing for Blender 5.1)
scene.display_settings.view_transform = 'AgX'
scene.display_settings.exposure = 0.0
scene.display_settings.gamma = 1.0

# Optional: add a soft fill light for better illumination
bpy.ops.object.light_add(type='AREA', location=(-5, -5, 6))
fill_light = bpy.context.active_object
fill_light.name = "FillLight"
fill_light.data.energy = 1.0
fill_light.data.size = 5.0

# Position camera for nice viewing angle
bpy.ops.object.camera_add(location=(6, 6, 5))
camera = bpy.context.active_object
camera.rotation_euler = (1.1, 0, 0.785)
scene.camera = camera

print("Floating island scene created successfully!")
