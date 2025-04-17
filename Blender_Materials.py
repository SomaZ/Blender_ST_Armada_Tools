import bpy
from . import Blender_Material_Nodes
from mathutils import Vector

def set_material_custom_properties(mat_node, sod_mat):
    material_group = mat_node.node_tree

    mat_node.inputs["Ambient Color"].default_value =  [*(sod_mat.ambient), 1.0]
    mat_node.inputs["Diffuse Color"].default_value =  [*(sod_mat.diffuse), 1.0]
    mat_node.inputs["Specular Color"].default_value =  [*(sod_mat.specular), 1.0]
    mat_node.inputs["Specular Power"].default_value =  sod_mat.specular_power
    mat_node.inputs["Lighting Model"].default_value =  sod_mat.lighting_model

    if "ST:A_Export" in material_group.nodes:
        material_group.nodes["ST:A_Export"].outputs[0].default_value = 1.0

def finish_mat(mat, texture_path, sod_materials):
    mat.use_nodes = True
    out_node = None
    for node in mat.node_tree.nodes.values():
        if node.type == 'BSDF_PRINCIPLED':
            out_node = node
            break
    if out_node is None:
        return
    
    out_node.inputs["Base Color"].default_value = [0.0, 0.0, 0.0, 1.0]
    out_node.inputs["IOR"].default_value = 1.0
    out_node.inputs["Emission Strength"].default_value = 1.0

    img_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    material = ""
    type = "default"
    try:
        material, image_name, cull, type = mat.name.split(".")
        image = bpy.data.images.get(image_name + ".tga")
        if image is None:
            image = bpy.data.images.load(texture_path + image_name + ".tga")
        img_node.image = image
        img_node.location = out_node.location + Vector([ -1200, 0])
        mat.use_backface_culling = True if cull == "1" else False
    except:
        print("Could not find image file for material:", mat.name)

    thresholded = False
    if material != "":
        mat_node = mat.node_tree.nodes.new(type="ShaderNodeGroup")
        mat_node.node_tree = Blender_Material_Nodes.Material_Node.get_node_tree(material)
        mat_node.name = "ST:A Material"
        mat.node_tree.links.new(mat_node.inputs[0], img_node.outputs["Color"])
        mat.node_tree.links.new(mat_node.inputs[1], img_node.outputs["Alpha"])
        mat_node.location = out_node.location + Vector([ -800, 0])
        img_node = mat_node
        if material in sod_materials:
            set_material_custom_properties(mat_node, sod_materials[material])
            if sod_materials[material].lighting_model != 0:
                thresholded = True

    if type == "alpha":
        mat.node_tree.links.new(out_node.inputs["Alpha"], img_node.outputs["Alpha"])
        mat.blend_method = "HASHED"
    elif type == "alphathreshold" or thresholded:
        math_threshold = mat.node_tree.nodes.new(type="ShaderNodeMath")
        math_threshold.operation = "GREATER_THAN"
        math_threshold.inputs[1].default_value = 0.5
        math_threshold.location = out_node.location + Vector([ -400, 0])
        mat.node_tree.links.new(math_threshold.inputs[0], img_node.outputs["Alpha"])
        mat.node_tree.links.new(out_node.inputs["Alpha"], math_threshold.outputs[0])
        mat.blend_method = "HASHED"
    elif type == "additive":
        transparent_node = mat.node_tree.nodes.new(type="ShaderNodeBsdfTransparent")
        transparent_node.location = out_node.location + Vector([ 0, 200])
        add_node = mat.node_tree.nodes.new(type="ShaderNodeAddShader")
        add_node.location = out_node.location + Vector([ 400, 0])
        mat.node_tree.links.new(add_node.inputs[0], transparent_node.outputs[0])
        mat.node_tree.links.new(add_node.inputs[1], out_node.outputs[0])

        mat_out_node = None
        for node in mat.node_tree.nodes.values():
            if node.type == 'OUTPUT_MATERIAL':
                mat_out_node = node
                break
        if mat_out_node is not None:
            mat_out_node.location = out_node.location + Vector([ 800, 0])
            mat.node_tree.links.new(add_node.outputs[0], mat_out_node.inputs[0])
        mat.blend_method = "BLEND"
    elif type == "translucent": # Untested, need to find examples where this is even used
        transparent_node = mat.node_tree.nodes.new(type="ShaderNodeBsdfTransparent")
        transparent_node.location = out_node.location + Vector([ 0, 200])
        mat.node_tree.links.new(transparent_node.inputs["Color"], img_node.outputs["Color"])
        mat_out_node = None
        for node in mat.node_tree.nodes.values():
            if node.type == 'OUTPUT_MATERIAL':
                mat_out_node = node
                break
        if mat_out_node is not None:
            mat.node_tree.links.new(transparent_node.outputs[0], mat_out_node.inputs[0])

        mat.blend_method = "BLEND"
    mat.node_tree.links.new(out_node.inputs["Emission Color"], img_node.outputs["Color"])

def finsh_object_materials(objects, texture_path, sod_materials):
    materials = set()
    for obj in objects:
        for mat in obj.data.materials:
            materials.add(mat)
    for mat in materials:
        finish_mat(mat, texture_path, sod_materials)