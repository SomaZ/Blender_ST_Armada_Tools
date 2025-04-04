import bpy

def set_material_custom_properties(mat, sod_mat):
    mat["STA_Export"] = True

    mat["STA_Ambient"] = [*sod_mat.ambient, 1.0]
    id_props = mat.id_properties_ui("STA_Ambient")
    id_props.update(description="The ambient color")
    id_props.update(subtype="COLOR_GAMMA")

    mat["STA_Diffuse"] = [*sod_mat.diffuse, 1.0]
    id_props = mat.id_properties_ui("STA_Diffuse")
    id_props.update(description="The diffuse color")
    id_props.update(subtype="COLOR_GAMMA")

    mat["STA_Specular"] = [*sod_mat.specular, 1.0]
    id_props = mat.id_properties_ui("STA_Specular")
    id_props.update(description="The specular color")
    id_props.update(subtype="COLOR_GAMMA")

    mat["STA_Specular_power"] = sod_mat.specular_power
    mat["STA_Lighting_model"] = sod_mat.lighting_model

def finish_mat(mat, texture_path, sod_materials):
    mat.use_nodes = True
    out_node = None
    for node in mat.node_tree.nodes.values():
        if node.type == 'BSDF_PRINCIPLED':
            out_node = node
            break
    if out_node is None:
        return
    img_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    material = ""
    try:
        material, image_name, cull, type = mat.name.split(".")
        img_node.image = bpy.data.images.load(texture_path + image_name + ".tga")
        mat.use_backface_culling = True if cull == "1" else False
    except:
        print("Could not find image file for material:", mat.name)

    if material in sod_materials:
        set_material_custom_properties(mat, sod_materials[material])
    mat.node_tree.links.new(out_node.inputs[0], img_node.outputs["Color"])

def finsh_object_materials(objects, texture_path, sod_materials):
    for obj in objects:
        for mat in obj.data.materials:
            finish_mat(mat, texture_path, sod_materials)