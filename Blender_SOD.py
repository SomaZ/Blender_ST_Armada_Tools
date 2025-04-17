import bpy
from mathutils import Matrix, Vector
from .SOD import *

rotation_mat = Matrix((
                [1.0, 0.0,  0.0,  0.0],
                [0.0, 0.0,  -1.0,  0.0],
                [0.0, 1.0,  0.0,  0.0],
                [0.0, 0.0,  0.0,  1.0]
                ))
inverse_rot_mat = rotation_mat.inverted()

def Import_SOD(sod):
    nodes = sod.nodes
    channels = sod.channels
    references = sod.references

    mesh_objects = []

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
            
            node_object = bpy.data.objects.new(mesh.name, mesh)
            bpy.context.collection.objects.link(node_object)

            mesh_objects.append(node_object)
            
            node_object.sta_dynamic_props.material_type = node.mesh.material
            node_object.sta_dynamic_props.texture_name = node.mesh.texture
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
            
        matrix = Matrix.Identity(4)
        matrix[0] = [*node.mat34[0:3], -node.mat34[9]]
        matrix[1] = [*node.mat34[3:6], node.mat34[10]]
        matrix[2] = [*node.mat34[6:9], node.mat34[11]]
        node_object.matrix_world = matrix
        if not node.root:
            node_object.matrix_world = rotation_mat @ matrix
            
        if node.root and node.root in bpy.data.objects:
            node_object.parent = bpy.data.objects[node.root]
    
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
            print("Could not find correct object parent for channel", channel.name)
            continue
            
        parent_matrix = parent_object.matrix_world
        
        node_object.sta_dynamic_props.animated = True
        node_object["start_frame"] = 1
        node_object["end_frame"] = len(channel.matrices)
        node_object["length"] = channel.length
        
        node_object.keyframe_insert('location', frame=0, group='LocRot')
        node_object.keyframe_insert('rotation_euler', frame=0, group='LocRot')
        
        for i in range(len(channel.matrices)):
            matrix = Matrix.Identity(4)
            matrix[0] = [*channel.matrices[i][0:3], -channel.matrices[i][9]]
            matrix[1] = [*channel.matrices[i][3:6], channel.matrices[i][10]]
            matrix[2] = [*channel.matrices[i][6:9], channel.matrices[i][11]]
            node_object.matrix_world = parent_matrix @ matrix
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
    current_positions = {}
    current_texture_coordinates = {}
    current_groups = {}

    for obj in objects:
        mesh = obj.evaluated_get(depsgraph).to_mesh()
        #mesh.transform(obj.matrix_world)

        if bpy.app.version < (4, 1, 0):
            mesh.calc_normals_split()

        mesh.calc_loop_triangles()
        positions = {}
        texture_coords = {}
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
                pos = v.co.copy().freeze()
                if mesh.has_custom_normals:
                    normal = l.normal.copy().freeze()
                else:
                    normal = v.normal.copy().freeze()
                tc = mesh.uv_layers.active.data[loop].uv.copy().freeze()
                
                pos_tuple = tuple([*pos, *normal])
                tex_tuple = tuple([*tc])
                positions[pos_tuple] = pos * Vector((-1, 1, 1))
                texture_coords[tex_tuple] = (tc[0], 1.0 - tc[1])
                pos_indexes.append(pos_tuple)
                tc_indexes.append(tex_tuple)

            if mat_name not in indices:
                indices[mat_name] = []
            indices[mat_name].append((pos_indexes, tc_indexes))

        group_fits = True
        for mat in indices:
            if mat in current_groups:
                if len(indices[mat]) + len(current_groups[mat]) > 65355:
                    group_fits = False
                    break
                
        if (len(current_positions) + len(positions) <= 65355 and 
            len(current_texture_coordinates) + len(texture_coords) <= 65355 and
            group_fits):

            current_positions |= positions
            current_texture_coordinates |= texture_coords

            for mat in indices:
                new_indices = []
                for ips, its in indices[mat]:
                    new_ips = [list(current_positions).index(i) for i in ips]
                    new_its = [list(current_texture_coordinates).index(i) for i in its]
                    new_indices.append((new_ips, new_its))
                mat_faces = [Face(indices, tc_indices) for indices, tc_indices in new_indices]

                if mat not in current_groups:
                    current_groups[mat] = Vertex_group(mat, mat_faces)
                else:
                    current_groups[mat].faces += mat_faces
            continue
        
        meshes.append(
            Mesh(
                material = obj.sta_dynamic_props.material_type,
                texture = obj.sta_dynamic_props.texture_name,
                cull_type = obj.sta_dynamic_props.face_cull,
                verts = current_positions.values(),
                tcs = current_texture_coordinates.values(),
                groups = current_groups.values()
            ))
        current_positions = {}
        current_texture_coordinates = {}
        current_groups = {}

    if len(current_positions) > 0:
        meshes.append(
            Mesh(
                material = obj.sta_dynamic_props.material_type,
                texture = obj.sta_dynamic_props.texture_name,
                cull_type = int(obj.sta_dynamic_props.face_cull),
                verts = current_positions.values(),
                tcs = current_texture_coordinates.values(),
                groups = current_groups.values()
            ))

    return meshes

def Add_new_sod_nodes(obj, nodes, texture_animated_objects, animated_objects):
    world_mat = obj.matrix_world
    parent_name = ""
    if obj.parent:
        parent_name = obj.parent.name
        world_mat = obj.parent.matrix_world.inverted() @ world_mat
    else:
        world_mat = inverse_rot_mat @ world_mat

    mat34 = [0.0]*12
    mat34[0:3] = world_mat[0][0:3]
    mat34[3:6] = world_mat[1][0:3]
    mat34[6:9] = world_mat[2][0:3]
    mat34[9] = -world_mat[0][3]
    mat34[10] = world_mat[1][3]
    mat34[11] = world_mat[2][3]

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
            tuple(mat_node.inputs["Ambient Color"].default_value[:3]),
            tuple(mat_node.inputs["Diffuse Color"].default_value[:3]),
            tuple(mat_node.inputs["Specular Color"].default_value[:3]),
            mat_node.inputs["Specular Power"].default_value,
            mat_node.inputs["Lighting Model"].default_value
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
    for obj in animated_objects:
        matrices = []
        for i in range(int(obj["start_frame"]), int(obj["end_frame"]) + 1):
            bpy.context.scene.frame_set(i)
            world_mat = obj.matrix_world
            if obj.parent:
                world_mat = obj.parent.matrix_world.inverted() @ world_mat
            else:
                world_mat = inverse_rot_mat @ world_mat
            mat34 = [0.0]*12
            mat34[0:3] = world_mat[0][0:3]
            mat34[3:6] = world_mat[1][0:3]
            mat34[6:9] = world_mat[2][0:3]
            mat34[9] = -world_mat[0][3]
            mat34[10] = world_mat[1][3]
            mat34[11] = world_mat[2][3]
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