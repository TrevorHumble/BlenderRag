import bpy
import math

# Clear default objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# ============================================================================
# MOODY INTERIOR CORNER SCENE
# ============================================================================

# Set render engine to Eevee (not BLENDER_EEVEE_NEXT — that doesn't exist in 5.1)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.use_volumetric = True
scene.eevee.volumetric_tile_size = '8x8'
scene.eevee.volumetric_samples = 64

# ============================================================================
# GEOMETRY: Floor and Walls
# ============================================================================

# Floor (large plane)
bpy.ops.mesh.primitive_plane_add(
    size=10.0,
    calc_uvs=True,
    enter_editmode=False,
    align='WORLD',
    location=(0.0, 0.0, 0.0),
    rotation=(0.0, 0.0, 0.0),
    scale=(1.0, 1.0, 1.0)
)
floor = bpy.context.active_object
floor.name = "Floor"

# Scale floor to be more rectangular for interior feel
floor.scale = (5.0, 4.0, 1.0)
bpy.ops.object.transform_apply(scale=True)

# Wall 1 (vertical, along Y)
bpy.ops.mesh.primitive_plane_add(
    size=8.0,
    calc_uvs=True,
    enter_editmode=False,
    align='WORLD',
    location=(-5.0, 0.0, 4.0),
    rotation=(0.0, math.radians(90.0), 0.0),
    scale=(1.0, 1.0, 1.0)
)
wall1 = bpy.context.active_object
wall1.name = "Wall1"
wall1.scale = (4.0, 4.0, 1.0)
bpy.ops.object.transform_apply(scale=True)

# Wall 2 (vertical, along X)
bpy.ops.mesh.primitive_plane_add(
    size=8.0,
    calc_uvs=True,
    enter_editmode=False,
    align='WORLD',
    location=(0.0, -4.0, 4.0),
    rotation=(math.radians(90.0), 0.0, 0.0),
    scale=(1.0, 1.0, 1.0)
)
wall2 = bpy.context.active_object
wall2.name = "Wall2"
wall2.scale = (5.0, 4.0, 1.0)
bpy.ops.object.transform_apply(scale=True)

# ============================================================================
# WINDOW (plane with special shader for light transmission)
# ============================================================================

bpy.ops.mesh.primitive_plane_add(
    size=2.0,
    calc_uvs=True,
    enter_editmode=False,
    align='WORLD',
    location=(0.0, -4.0, 3.0),
    rotation=(math.radians(90.0), 0.0, 0.0),
    scale=(1.0, 1.0, 1.0)
)
window = bpy.context.active_object
window.name = "Window"
window.location.y = -4.01

# ============================================================================
# EMISSIVE LAMP
# ============================================================================

bpy.ops.object.light_add(
    type='POINT',
    radius=0.5,
    align='WORLD',
    location=(2.0, -2.0, 2.5),
    rotation=(0.0, 0.0, 0.0),
    scale=(1.0, 1.0, 1.0)
)
lamp = bpy.context.active_object
lamp.name = "EmissiveLamp"
lamp.data.energy = 500.0
lamp.data.color = (0.9, 0.8, 0.6)  # Warm color

# ============================================================================
# VOLUMETRIC FOG ENCLOSURE
# ============================================================================
# Important: World volumes drop in final render in Eevee. Use a large mesh cube instead.

bpy.ops.mesh.primitive_cube_add(
    size=120.0,
    calc_uvs=True,
    enter_editmode=False,
    align='WORLD',
    location=(0.0, 0.0, 30.0),
    rotation=(0.0, 0.0, 0.0),
    scale=(1.0, 1.0, 1.0)
)
fog_cube = bpy.context.active_object
fog_cube.name = "VolumetricFog"

# Create volumetric material for fog cube
fog_mat = bpy.data.materials.new("VolumeFog")
fog_mat.use_nodes = True
fog_mat.node_tree.nodes.clear()

# Add Volume Scatter shader for atmosphere
vol_node = fog_mat.node_tree.nodes.new('ShaderNodeVolumeScatter')
vol_node.inputs['Color'].default_value = (0.8, 0.75, 0.7, 1.0)  # Warm beige
vol_node.inputs['Density'].default_value = 0.15  # Subtle density for moody effect

output_node = fog_mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
fog_mat.node_tree.links.new(vol_node.outputs['Volume'], output_node.inputs['Volume'])

# Assign material to fog cube
fog_cube.data.materials.append(fog_mat)

# ============================================================================
# MATERIALS
# ============================================================================

# Dark concrete floor material
floor_mat = bpy.data.materials.new("FloorConcrete")
floor_mat.use_nodes = True
floor_mat.node_tree.nodes.clear()

bsdf = floor_mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
bsdf.inputs['Base Color'].default_value = (0.15, 0.15, 0.15, 1.0)
bsdf.inputs['Roughness'].default_value = 0.9

output = floor_mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
floor_mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

floor.data.materials.append(floor_mat)

# Textured wall material (dark with slight variation)
wall_mat = bpy.data.materials.new("WallPlaster")
wall_mat.use_nodes = True
wall_mat.node_tree.nodes.clear()

bsdf = wall_mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
bsdf.inputs['Base Color'].default_value = (0.25, 0.22, 0.2, 1.0)
bsdf.inputs['Roughness'].default_value = 0.85

output = wall_mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
wall_mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

wall1.data.materials.append(wall_mat)
wall2.data.materials.append(wall_mat)

# Frosted glass window material (translucent with slight emission)
window_mat = bpy.data.materials.new("FrostedGlass")
window_mat.use_nodes = True
window_mat.node_tree.nodes.clear()

bsdf = window_mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
bsdf.inputs['Base Color'].default_value = (0.7, 0.75, 0.8, 1.0)
bsdf.inputs['Roughness'].default_value = 0.5
bsdf.inputs['Transmission'].default_value = 0.8

output = window_mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
window_mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

window.data.materials.append(window_mat)

# ============================================================================
# SUNLIGHT THROUGH WINDOW
# ============================================================================
# Add a sun light positioned to stream through the window

bpy.ops.object.light_add(
    type='SUN',
    radius=2.0,
    align='WORLD',
    location=(10.0, -15.0, 10.0),
    rotation=(math.radians(45.0), math.radians(-60.0), 0.0),
    scale=(1.0, 1.0, 1.0)
)
sun = bpy.context.active_object
sun.name = "SunlightThruWindow"
sun.data.energy = 2.0
sun.data.angle = math.radians(1.5)
sun.data.color = (1.0, 0.95, 0.85)  # Warm daylight

# ============================================================================
# WORLD BACKGROUND (dark, minimal)
# ============================================================================

world = bpy.data.worlds["World"]
world.use_nodes = True
world.node_tree.nodes.clear()

bg = world.node_tree.nodes.new('ShaderNodeBackground')
bg.inputs['Color'].default_value = (0.05, 0.05, 0.08, 1.0)  # Very dark blue-gray
bg.inputs['Strength'].default_value = 0.3

world_output = world.node_tree.nodes.new('ShaderNodeOutputWorld')
world.node_tree.links.new(bg.outputs['Background'], world_output.inputs['Surface'])

# ============================================================================
# CAMERA POSITIONING
# ============================================================================

bpy.ops.object.camera_add(
    enter_editmode=False,
    align='WORLD',
    location=(2.5, 1.5, 1.2),
    rotation=(math.radians(15.0), 0.0, math.radians(-25.0))
)
camera = bpy.context.active_object
camera.name = "Camera"
scene.camera = camera

print("Moody interior corner scene created successfully!")
