import bpy
from mathutils import Matrix, Vector

rotation_mat = Matrix((
                [1.0, 0.0,  0.0,  0.0],
                [0.0, 0.0,  -1.0,  0.0],
                [0.0, 1.0,  0.0,  0.0],
                [0.0, 0.0,  0.0,  1.0]
                ))

def ImportSOD(sod):
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
            
            node_object["material"] = node.mesh.material
            node_object["texture"] = node.mesh.texture
            node_object["cull_type"] = node.mesh.cull_type
            node_object["texture_animation"] = False

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
        node_object["animated"] = False
            
        matrix = Matrix.Identity(4)
        matrix[0] = [*node.mat34[0:3], -node.mat34[9]]
        matrix[1] = [*node.mat34[3:6], node.mat34[10]]
        matrix[2] = [*node.mat34[6:9], node.mat34[11]]
        node_object.matrix_world = matrix
        if not node.root:
            node_object.matrix_world = rotation_mat @ matrix
            root_matrix = node_object.matrix_world
            
        if node.root and node.root in bpy.data.objects:
            node_object.parent = bpy.data.objects[node.root]
    
    # Parse animations
    bpy.context.scene.frame_end = 1
    for channel in list(channels.values())[::-1]:
        
        node_object = bpy.data.objects.get(channel.name)
        if not node_object:
            print("Could not find correct animation object node for channel", channel.name)
            continue
        
        parent_object = node_object.parent
        if not parent_object:
            print("Could not find correct object parent for channel", channel.name)
            continue
            
        parent_matrix = parent_object.matrix_world
        
        node_object["animated"] = True
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
        node_object["texture_animation"] = True
        node_object["ref_animation"] = ref.anim
        node_object["ref_type"] = ref.type
        node_object["ref_offset"] = ref.offset

    return mesh_objects