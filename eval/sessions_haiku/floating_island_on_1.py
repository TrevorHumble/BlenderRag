import bpy
import bmesh
import math
import random

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.world.use_nodes = True

view_settings = scene.display_settings.view_transform
view_settings = 'AgX'
scene.display_settings.view_transform = view_settings

mesh_data = bpy.data.meshes.new('IslandBase')
island = bpy.data.objects.new('FloatingIsland', mesh_data)
bpy.context.collection.objects.link(island)
bpy.context.view_layer.objects.active = island
island.select_set(True)

bm = bmesh.new()
bmesh.ops.create_icosphere(bm, subdivisions=3, radius=2.5)
bm.to_mesh(mesh_data)
mesh_data.update()
bm.free()

bpy.context.view_layer.objects.active = island
island.select_set(True)
bpy.ops.object.shade_smooth()

mat_rock = bpy.data.materials.new(name='RockMaterial')
mat_rock.use_nodes = True
bsdf = mat_rock.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (0.45, 0.42, 0.38, 1.0)
bsdf.inputs['Roughness'].default_value = 0.8
island.data.materials.append(mat_rock)

mat_grass = bpy.data.materials.new(name='GrassMaterial')
mat_grass.use_nodes = True
bsdf_grass = mat_grass.node_tree.nodes['Principled BSDF']
bsdf_grass.inputs['Base Color'].default_value = (0.15, 0.35, 0.12, 1.0)
bsdf_grass.inputs['Roughness'].default_value = 0.7
bsdf_grass.inputs['Subsurface Weight'].default_value = 0.05
island.data.materials.append(mat_grass)

bpy.context.view_layer.objects.active = island
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
mesh_data = island.data
face_count = len(mesh_data.polygons)
half_count = face_count // 2

bpy.ops.mesh.select_all(action='DESELECT')
for i, poly in enumerate(mesh_data.polygons):
    if poly.center.z > 0.5:
        poly.select = True

bpy.context.view_layer.objects.active = island
bpy.ops.object.material_slot_select()
island.material_slots[1].material = mat_grass
bpy.ops.object.mode_set(mode='OBJECT')

sub_mod = island.modifiers.new(name='Subdivision', type='SUBSURF')
sub_mod.levels = 2
sub_mod.render_levels = 3

island.location = (0, 0, 0)

def create_low_poly_tree(name, location):
    mesh = bpy.data.meshes.new(f'{name}_mesh')
    tree_obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(tree_obj)

    bm = bmesh.new()

    base_mat = bpy.data.materials.new(name=f'{name}_trunk')
    base_mat.use_nodes = True
    base_bsdf = base_mat.node_tree.nodes['Principled BSDF']
    base_bsdf.inputs['Base Color'].default_value = (0.4, 0.25, 0.1, 1.0)
    base_bsdf.inputs['Roughness'].default_value = 0.9
    tree_obj.data.materials.append(base_mat)

    foliage_mat = bpy.data.materials.new(name=f'{name}_foliage')
    foliage_mat.use_nodes = True
    foliage_bsdf = foliage_mat.node_tree.nodes['Principled BSDF']
    foliage_bsdf.inputs['Base Color'].default_value = (0.2, 0.45, 0.15, 1.0)
    foliage_bsdf.inputs['Roughness'].default_value = 0.6
    tree_obj.data.materials.append(foliage_mat)

    trunk_height = 0.5
    trunk_radius = 0.12

    v_base = bm.verts.new((0, 0, 0))
    v_top = bm.verts.new((0, 0, trunk_height))

    angles = [0, 90, 180, 270]
    for angle in angles:
        rad = math.radians(angle)
        x = trunk_radius * math.cos(rad)
        y = trunk_radius * math.sin(rad)
        bm.verts.new((x, y, 0))
        bm.verts.new((x, y, trunk_height))

    for i in range(4):
        v1 = bm.verts[1 + i*2]
        v2 = bm.verts[1 + ((i+1)%4)*2]
        v3 = bm.verts[2 + ((i+1)%4)*2]
        v4 = bm.verts[2 + i*2]
        face = bm.faces.new([v1, v2, v3, v4])
        face.material_index = 0

    foliage_center = bm.verts.new((0, 0, trunk_height + 0.3))
    foliage_radius = 0.4
    foliage_verts = []
    for i in range(6):
        angle = math.radians(i * 60)
        x = foliage_radius * math.cos(angle)
        y = foliage_radius * math.sin(angle)
        z = trunk_height + 0.2 + random.uniform(-0.1, 0.1)
        foliage_verts.append(bm.verts.new((x, y, z)))

    for i in range(6):
        v1 = foliage_verts[i]
        v2 = foliage_verts[(i+1) % 6]
        face = bm.faces.new([foliage_center, v1, v2])
        face.material_index = 1

    bm.to_mesh(mesh)
    mesh.update()
    bm.free()

    tree_obj.location = location
    bpy.context.view_layer.objects.active = tree_obj
    tree_obj.select_set(True)
    bpy.ops.object.shade_smooth()

    return tree_obj

tree1 = create_low_poly_tree('Tree_1', (-1.5, 0.8, 2.0))
tree2 = create_low_poly_tree('Tree_2', (1.2, -1.1, 2.0))

sun_light = bpy.data.lights.new(name='Sun', type='SUN')
sun_light.energy = 2.0
sun_light.angle = 0.05
sun_obj = bpy.data.objects.new(name='SunLight', object_data=sun_light)
bpy.context.collection.objects.link(sun_obj)
sun_obj.location = (3.0, 4.0, 5.0)
sun_obj.rotation_euler = (math.radians(45), math.radians(30), 0)

ambient_light = bpy.data.lights.new(name='Ambient', type='SUN')
ambient_light.energy = 0.3
ambient_obj = bpy.data.objects.new(name='AmbientLight', object_data=ambient_light)
bpy.context.collection.objects.link(ambient_obj)
ambient_obj.location = (-2.0, -2.0, 2.0)
ambient_obj.rotation_euler = (math.radians(135), math.radians(45), 0)

bpy.context.view_layer.objects.active = island
island.select_set(True)
