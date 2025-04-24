import bpy
from mathutils import Matrix, Vector
from numpy import array, dot, sqrt
from .SOD import *

rotation_mat = Matrix((
                [1.0, 0.0,  0.0,  0.0],
                [0.0, 0.0,  -1.0,  0.0],
                [0.0, 1.0,  0.0,  0.0],
                [0.0, 0.0,  0.0,  1.0]
                ))
inverse_rot_mat = Matrix((
                [1.0, 0.0,  0.0,  0.0],
                [0.0, 0.0,  1.0,  0.0],
                [0.0, -1.0,  0.0,  0.0],
                [0.0, 0.0,  0.0,  1.0]
                ))

def normalize(vector):
    sqr_length = dot(vector, vector)
    if sqr_length == 0.0:
        return array((0.0, 0.0, 0.0))
    return vector / sqrt(sqr_length)

def mat34_to_blender(mat34):
    matrix = Matrix.Identity(4)
    matrix.col[0] = [*mat34[0:3], 0.0]
    matrix.col[1] = [*mat34[3:6], 0.0]
    matrix.col[2] = [*mat34[6:9], 0.0]
    matrix.col[3] = [*mat34[9:12], 1.0]
    matrix.col[0] *= -1.0
    matrix.row[0] *= -1.0
    return matrix

def mat34_from_blender(matrix):
    export_matrix = matrix.copy()
    export_matrix.row[0] *= -1.0
    export_matrix.col[0] *= -1.0
    mat34 = [0.0]*12
    mat34[0:3] = normalize(export_matrix.col[0][0:3])
    mat34[3:6] = normalize(export_matrix.col[1][0:3])
    mat34[6:9] = normalize(export_matrix.col[2][0:3])
    mat34[9:12] = export_matrix.col[3][0:3]
    return mat34

def Import_SOD(sod):
    nodes = sod.nodes
    channels = sod.channels
    references = sod.references

    objects = []
    mesh_objects = []
    root_node_name = "root"

    # Parse mesh data
    for node in nodes.values():
        node_object = None
        if node.type == 1:
            vertices = [Vector(v) * Vector((-1, 1, 1)) for v in node.mesh.verts]
            indices = []
            tcs = []
            material_ids = []
            materials = []
            
            for group in node.mesh.groups:
                mat = "{}.{}.{}.{}".format(group.material, node.mesh.texture, node.mesh.cull_type, node.mesh.material)
                if mat not in materials:
                    materials.append(mat)
                mat_index = materials.index(mat)
                for face in group.faces:
                    indices.append(face.indices)
                    face_tcs = [node.mesh.tcs[index] for index in face.tc_indices]
                    for face_tc in face_tcs:
                        tcs.append(face_tc[0])
                        tcs.append(1.0-face_tc[1])
                    material_ids.append(mat_index)
            
            mesh = bpy.data.meshes.new(node.name)
            mesh.from_pydata(vertices, [], indices)
            
            for mat_name in materials:
                mat = bpy.data.materials.get(mat_name)
                if (mat is None):
                    mat = bpy.data.materials.new(name=mat_name)
                
                mesh.materials.append(mat)
            
            mesh.polygons.foreach_set("material_index", material_ids)
            
            mesh.uv_layers.new(do_init=False, name="UVMap")
            mesh.uv_layers["UVMap"].data.foreach_set("uv", tcs)
            
            if bpy.app.version < (4, 1, 0):
                mesh.use_auto_smooth = True

            for poly in mesh.polygons:
                poly.use_smooth = True
            
            node_object = bpy.data.objects.new(node.name, mesh)
            bpy.context.collection.objects.link(node_object)

            mesh_objects.append(node_object)
            
            node_object.sta_dynamic_props.material_type = node.mesh.material if node.mesh.material else "default"
            node_object.sta_dynamic_props.texture_name = node.mesh.texture if node.mesh.texture else ""
            node_object.sta_dynamic_props.face_cull = str(node.mesh.cull_type)
            node_object.sta_dynamic_props.texture_animated = False
        elif node.type == 12:
            bpy.ops.object.empty_add(type="ARROWS")
            tag_obj = bpy.context.object
            tag_obj.name = node.name
            node_object = tag_obj
            node_object["emitter"] = node.emitter
        else:
            bpy.ops.object.empty_add(type="ARROWS")
            tag_obj = bpy.context.object
            tag_obj.name = node.name
            node_object = tag_obj
            
        node_object["node_type"] = node.type
        node_object.sta_dynamic_props.animated = False
        
        matrix = mat34_to_blender(node.mat34)
        node_object.matrix_world = matrix

        if not node.root or node.root == "":
            root_node_name = node.name

        if node.root and node.root in bpy.data.objects:
            if node.root == root_node_name:
                node_object.matrix_world = rotation_mat @ matrix
            node_object.parent = bpy.data.objects[node.root]

        objects.append(node_object)

    # Parse animations
    bpy.context.scene.frame_end = 1
    for channel in list(channels.values())[::-1]:

        if not len(channel.matrices):
            continue
        
        node_object = bpy.data.objects.get(channel.name)
        if not node_object:
            print("Could not find correct animation object node for channel", channel.name)
            continue
        
        parent_object = node_object.parent
        if not parent_object:
            parent_matrix = Matrix.Identity(4)
        else:
            parent_matrix = parent_object.matrix_world
            if parent_object.name == root_node_name:
                parent_matrix = rotation_mat @ parent_matrix
        
        node_object.sta_dynamic_props.animated = True
        node_object["start_frame"] = 1
        node_object["end_frame"] = len(channel.matrices)
        node_object["length"] = channel.length
        
        node_object.keyframe_insert('location', frame=0, group='LocRot')
        node_object.keyframe_insert('rotation_euler', frame=0, group='LocRot')
        
        for i in range(len(channel.matrices)):
            node_object.matrix_world = parent_matrix @ mat34_to_blender(channel.matrices[i])
            node_object.keyframe_insert('location', frame=i+1, group='LocRot')
            node_object.keyframe_insert('rotation_euler', frame=i+1, group='LocRot')

        bpy.context.scene.frame_end = max(bpy.context.scene.frame_end, len(channel.matrices))
        
    # Parse texture animation info
    for ref in references.values():
        node_object = bpy.data.objects.get(ref.node)
        node_object.sta_dynamic_props.texture_animated = True
        node_object["ref_animation"] = ref.anim
        node_object["ref_type"] = ref.type
        node_object["ref_offset"] = ref.offset

    return mesh_objects

def Get_material_name(mat):
    if mat is None:
        return "default"
        
    if "ST:A Material" not in mat.node_tree.nodes:
        return mat.name.split(".")[0]

    material_node = mat.node_tree.nodes["ST:A Material"]
    return material_node.node_tree.name

def Make_meshes_from_objects(objects):
    meshes = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    current_positions = []
    current_texture_coordinates = []
    current_groups = {}
    current_position_indices = {}
    current_tc_indices = {}

    for obj in objects:
        mesh = obj.evaluated_get(depsgraph).to_mesh()

        loc, rot, sca = obj.matrix_world.decompose()

        if bpy.app.version < (4, 1, 0):
            mesh.calc_normals_split()

        mesh.calc_loop_triangles()
        positions = []
        texture_coords = []
        indices = {}

        for triangle in mesh.loop_triangles:
            if len(mesh.materials) == 0:
                mat_name = "default"
            else:
                mat = mesh.materials[triangle.material_index]
                mat_name = Get_material_name(mat)

            pos_indexes = []
            tc_indexes = []
            for vert, loop in zip(triangle.vertices, triangle.loops):
                v = mesh.vertices[vert]
                l = mesh.loops[loop]
                pos = v.co.copy().freeze() * sca
                normal = l.normal.copy().freeze()
                tc = mesh.uv_layers.active.data[loop].uv.copy().freeze()
                
                pos_tuple = tuple([*pos, *normal])
                tex_tuple = tuple([*tc])
                if pos_tuple not in current_position_indices:
                    index = len(positions) + len(current_positions)
                    positions.append(pos * Vector((-1, 1, 1)))
                    current_position_indices[pos_tuple] = index
                pos_indexes.append(current_position_indices[pos_tuple])

                if tex_tuple not in current_tc_indices:
                    index = len(texture_coords) + len(current_texture_coordinates)
                    texture_coords.append((tc[0], 1.0 - tc[1]))
                    current_tc_indices[tex_tuple] = index
                tc_indexes.append(current_tc_indices[tex_tuple])

            if mat_name not in indices:
                indices[mat_name] = []
            indices[mat_name].append((pos_indexes, tc_indexes))

        group_fits = True
        for mat in indices:
            if mat in current_groups:
                if len(indices[mat]) + len(current_groups[mat]) > 65355:
                    group_fits = False
                    break
                
        # If everything still fits into one mesh, add everything and continue
        if (len(current_positions) + len(positions) <= 65355 and 
            len(current_texture_coordinates) + len(texture_coords) <= 65355 and
            group_fits):

            current_positions += positions
            current_texture_coordinates += texture_coords

            for mat in indices:
                mat_faces = [Face(indices, tc_indices) for indices, tc_indices in indices[mat]]

                if mat not in current_groups:
                    current_groups[mat] = Vertex_group(mat, mat_faces)
                else:
                    current_groups[mat].faces += mat_faces
            continue
        
        # If new stuff doesnt fit anymore, create mesh for the old data
        meshes.append(
            Mesh(
                material = obj.sta_dynamic_props.material_type,
                texture = obj.sta_dynamic_props.texture_name,
                cull_type = obj.sta_dynamic_props.face_cull,
                verts = current_positions,
                tcs = current_texture_coordinates,
                groups = current_groups.values()
            ))

        # Redo current object...
        current_position_indices = {}
        current_tc_indices = {}
        current_positions = []
        current_texture_coordinates = []
        current_groups = {}

        positions = []
        texture_coords = []
        indices = {}

        for triangle in mesh.loop_triangles:
            if len(mesh.materials) == 0:
                mat_name = "default"
            else:
                mat = mesh.materials[triangle.material_index]
                mat_name = Get_material_name(mat)

            pos_indexes = []
            tc_indexes = []
            for vert, loop in zip(triangle.vertices, triangle.loops):
                v = mesh.vertices[vert]
                l = mesh.loops[loop]
                pos = v.co.copy().freeze() * sca
                if mesh.has_custom_normals:
                    normal = l.normal.copy().freeze()
                else:
                    normal = v.normal.copy().freeze()
                tc = mesh.uv_layers.active.data[loop].uv.copy().freeze()
                
                pos_tuple = tuple([*pos, *normal])
                tex_tuple = tuple([*tc])
                if pos_tuple not in current_position_indices:
                    index = len(positions) + len(current_position_indices)
                    positions.append(pos * Vector((-1, 1, 1)))
                    current_position_indices[pos_tuple] = index
                pos_indexes.append(current_position_indices[pos_tuple])

                if tex_tuple not in current_tc_indices:
                    index = len(texture_coords) + len(current_tc_indices)
                    texture_coords.append((tc[0], 1.0 - tc[1]))
                    current_tc_indices[tex_tuple] = index
                tc_indexes.append(current_tc_indices[tex_tuple])

            if mat_name not in indices:
                indices[mat_name] = []
            indices[mat_name].append((pos_indexes, tc_indexes))
        
        current_positions += positions
        current_texture_coordinates += texture_coords
        for mat in indices:
            mat_faces = [Face(indices, tc_indices) for indices, tc_indices in indices[mat]]
            if mat not in current_groups:
                current_groups[mat] = Vertex_group(mat, mat_faces)
            else:
                current_groups[mat].faces += mat_faces

    if len(current_positions) > 0:
        meshes.append(
            Mesh(
                material = obj.sta_dynamic_props.material_type,
                texture = obj.sta_dynamic_props.texture_name,
                cull_type = int(obj.sta_dynamic_props.face_cull),
                verts = current_positions,
                tcs = current_texture_coordinates,
                groups = current_groups.values()
            ))

    return meshes

def Add_new_sod_nodes(obj, nodes, texture_animated_objects, animated_objects):
    world_mat = obj.matrix_world
    parent_name = ""
    if obj.parent:
        parent_name = obj.parent.name
        world_mat = obj.parent.matrix_world.inverted() @ world_mat
        if parent_name == "root":
            world_mat = inverse_rot_mat @ world_mat
    else:
        world_mat = Matrix.Identity(4)

    mat34 = mat34_from_blender(world_mat)
    node_type = 0
    if "node_type" in obj:
        node_type = int(obj["node_type"])
    elif obj.type == "MESH":
        node_type = 1
    elif "emitter" in obj:
        node_type = 12

    processed_children = []
    
    if node_type == 12:
        if "emitter" in obj and len(obj["emitter"]) > 0:
            nodes[obj.name] = Node(
            type = node_type,
            name = obj.name,
            root = parent_name,
            mat34=mat34,
            emitter = str(obj["emitter"])
            )
        else:
            print("Emitter type without emitter set")
    elif node_type == 1:
        if obj.sta_dynamic_props.texture_animated:
            texture_animated_objects.append(obj)

        new_mesh = Make_meshes_from_objects([obj])[0]
        nodes[obj.name] = Node(
            type = node_type,
            name = obj.name,
            root = parent_name,
            mat34=mat34,
            mesh=new_mesh
        )
    else:
        nodes[obj.name] = Node(
            type = node_type,
            name = obj.name,
            root = parent_name,
            mat34=mat34
        )

    if obj.sta_dynamic_props.animated:
        animated_objects.append(obj)

    # TODO: gather mesh children when merge is enabled

    for child in obj.children:
        if child in processed_children:
            continue
        Add_new_sod_nodes(child, nodes, texture_animated_objects, animated_objects)


def Export_SOD(file_path, version = 1.8):

    new_sod = SOD(version)
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue

        if "ST:A Material" not in mat.node_tree.nodes:
            continue

        mat_node = mat.node_tree.nodes["ST:A Material"]

        if "ST:A_Export" not in mat_node.node_tree.nodes:
            continue
        if mat_node.node_tree.nodes["ST:A_Export"].outputs[0].default_value != 1.0:
            continue

        new_sod.materials[mat_node.node_tree.name] = Material(
            mat_node.node_tree.name,
            tuple(mat_node.node_tree.interface.items_tree["Ambient Color"].default_value[:3]),
            tuple(mat_node.node_tree.interface.items_tree["Diffuse Color"].default_value[:3]),
            tuple(mat_node.node_tree.interface.items_tree["Specular Color"].default_value[:3]),
            mat_node.node_tree.interface.items_tree["Specular Power"].default_value,
            mat_node.node_tree.interface.items_tree["Lighting Model"].default_value
        )
    
    if "root" not in bpy.context.scene.objects:
        print("No root object found. Writing materials only")
        new_sod.to_file(file_path)
        return
    
    texture_animated_objects = []
    animated_objects = []
    Add_new_sod_nodes(
        bpy.context.scene.objects["root"],
        new_sod.nodes,
        texture_animated_objects,
        animated_objects)

    # add animations
    for obj in animated_objects[::-1]:
        matrices = []
        for i in range(int(obj["start_frame"]), int(obj["end_frame"]) + 1):
            bpy.context.scene.frame_set(i)
            world_mat = obj.matrix_world
            if obj.parent:
                world_mat = obj.parent.matrix_world.inverted() @ world_mat
                if obj.parent.name == "root":
                    world_mat = inverse_rot_mat @ world_mat
            else:
                world_mat = Matrix.Identity(4)

            mat34 = mat34_from_blender(world_mat)
            matrices.append(mat34)

        new_sod.channels[obj.name] = Animation_channel(
            name = obj.name,
            length = obj["length"],
            matrices=matrices
        )

    # add references
    for obj in texture_animated_objects:
        new_sod.references[obj.name] = Animation_reference(
            type = obj["ref_type"],
            node = obj.name,
            anim = obj["ref_animation"],
            offset= obj["ref_offset"]
        )

    new_sod.to_file(file_path)
    return