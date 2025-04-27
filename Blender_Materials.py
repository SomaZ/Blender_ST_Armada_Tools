import bpy
from . import Blender_Material_Nodes
from mathutils import Vector

def set_material_drivers(mat_node):
    material_group = mat_node.node_tree
    values = ("Specular Power", "Lighting Model")
    for v in values:
        driver = mat_node.inputs[v].driver_add("default_value")
        var = driver.driver.variables.new()
        var.name = v.replace(" ", "")
        var.type = 'SINGLE_PROP'
        var.targets[0].id_type = "NODETREE"
        var.targets[0].id = material_group
        if bpy.app.version >= (4, 0, 0):
            var.targets[0].data_path = 'interface.items_tree["{}"].default_value'.format(v)
        else:
            var.targets[0].data_path = 'inputs["{}"].default_value'.format(v)
        driver.driver.expression = var.name

    values = ("Ambient Color", "Diffuse Color", "Specular Color")
    for v in values:
        driver = mat_node.inputs[v].driver_add("default_value")
        for i in range(3):
            var = driver[i].driver.variables.new()
            var.name = v.replace(" ", "")
            var.type = 'SINGLE_PROP'
            var.targets[0].id_type = "NODETREE"
            var.targets[0].id = material_group
            if bpy.app.version >= (4, 0, 0):
                var.targets[0].data_path = 'interface.items_tree["{}"].default_value[{}]'.format(v, i)
            else:
                var.targets[0].data_path = 'inputs["{}"].default_value[{}]'.format(v, i)
            driver[i].driver.expression = var.name

def set_material_custom_properties(mat_node, sod_mat):
    material_group = mat_node.node_tree
    if bpy.app.version >= (4, 0, 0):
        material_group.interface.items_tree["Ambient Color"].default_value =  [*(sod_mat.ambient), 1.0]
        material_group.interface.items_tree["Diffuse Color"].default_value =  [*(sod_mat.diffuse), 1.0]
        material_group.interface.items_tree["Specular Color"].default_value =  [*(sod_mat.specular), 1.0]
        material_group.interface.items_tree["Specular Power"].default_value =  sod_mat.specular_power
        material_group.interface.items_tree["Lighting Model"].default_value =  sod_mat.lighting_model
    else:
        material_group.inputs["Ambient Color"].default_value =  [*(sod_mat.ambient), 1.0]
        material_group.inputs["Diffuse Color"].default_value =  [*(sod_mat.diffuse), 1.0]
        material_group.inputs["Specular Color"].default_value =  [*(sod_mat.specular), 1.0]
        material_group.inputs["Specular Power"].default_value =  sod_mat.specular_power
        material_group.inputs["Lighting Model"].default_value =  sod_mat.lighting_model
        
    if "ST:A_Export" in material_group.nodes:
        material_group.nodes["ST:A_Export"].outputs[0].default_value = 1.0

def finish_mat(mat, texture_path, sod_materials, img_node = None, mat_node = None):
    mat.use_nodes = True
    out_node = None
    for node in mat.node_tree.nodes.values():
        if node.type == 'BSDF_PRINCIPLED':
            out_node = node
            break
    if out_node is None:
        return
    
    out_node.inputs["Base Color"].default_value = [0.0, 0.0, 0.0, 1.0]
    if bpy.app.version >= (4, 0, 0):
        out_node.inputs["IOR"].default_value = 1.0
        out_node.inputs["Emission Strength"].default_value = 1.0
    else:
        out_node.inputs["Specular"].default_value = 0.0

    if img_node is None:
        img_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    material = ""
    type = "default"
    try:
        props = mat.name.split(".")
        if len(props) == 4:
            material, image_name, cull, type = props
        elif len(props) > 4:
            material, image_name, cull, type = props[:4]

        type = type.strip()

        image = bpy.data.images.get(image_name + ".tga")
        if image is None:
            image = bpy.data.images.load(texture_path + image_name + ".tga")
        img_node.image = image
        img_node.location = out_node.location + Vector([ -1200, 0])
        img_node.image.alpha_mode = 'CHANNEL_PACKED'
        mat.use_backface_culling = True if cull == "1" else False
    except Exception as e:
        print(e)
        print("Could not find image file for material:", mat.name)

    thresholded = False
    if material != "":
        if mat_node is None:
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
        set_material_drivers(mat_node)

    mat_out_node = None
    for node in mat.node_tree.nodes.values():
        if node.type == 'OUTPUT_MATERIAL':
            mat_out_node = node
            break

    if type == "alpha":
        mat.node_tree.links.new(out_node.inputs["Alpha"], img_node.outputs["Alpha"])
        mat.blend_method = "HASHED"
    elif type == "additive":
        transparent_node = mat.node_tree.nodes.new(type="ShaderNodeBsdfTransparent")
        transparent_node.location = out_node.location + Vector([ 0, 200])
        add_node = mat.node_tree.nodes.new(type="ShaderNodeAddShader")
        add_node.location = out_node.location + Vector([ 400, 0])
        mat.node_tree.links.new(add_node.inputs[0], transparent_node.outputs[0])
        mat.node_tree.links.new(add_node.inputs[1], out_node.outputs[0])
        
        if mat_out_node is not None:
            mat_out_node.location = out_node.location + Vector([ 800, 0])
            mat.node_tree.links.new(add_node.outputs[0], mat_out_node.inputs[0])
        mat.blend_method = "BLEND"
    elif type == "translucent": # Untested, need to find examples where this is even used
        math_mult = mat.node_tree.nodes.new(type="ShaderNodeMath")
        math_mult.operation = "MULTIPLY"
        math_mult.inputs[1].default_value = 0.5
        math_mult.location = out_node.location + Vector([ -400, 0])
        mat.node_tree.links.new(out_node.inputs["Alpha"], math_mult.outputs[0])
        mat.node_tree.links.new(math_mult.inputs[0], img_node.outputs["Alpha"])
        out_node.inputs["Alpha"].default_value = 0.5
        mat.blend_method = "BLEND"
    elif type == "wireframe":
        wire_node = mat.node_tree.nodes.new(type="ShaderNodeWireframe")
        wire_node.location = out_node.location + Vector([ -400, 200])
        wire_node.inputs["Size"].default_value = 0.1
        mat.node_tree.links.new(out_node.inputs["Alpha"], wire_node.outputs[0])
        mat.blend_method = "HASHED"
    elif type != "opaque":
        math_threshold = mat.node_tree.nodes.new(type="ShaderNodeMath")
        math_threshold.operation = "GREATER_THAN"
        math_threshold.inputs[1].default_value = 0.5
        math_threshold.location = out_node.location + Vector([ -400, 0])
        mat.node_tree.links.new(math_threshold.inputs[0], img_node.outputs["Alpha"])
        mat.node_tree.links.new(out_node.inputs["Alpha"], math_threshold.outputs[0])
        if mat_out_node is not None:
            mat.node_tree.links.new(out_node.outputs[0], mat_out_node.inputs[0])
        mat.blend_method = "HASHED"
    
    if bpy.app.version >= (4, 0, 0):
        mat.node_tree.links.new(out_node.inputs["Emission Color"], img_node.outputs["Color"])
    else:
        mat.node_tree.links.new(out_node.inputs["Emission"], img_node.outputs["Color"])

def finsh_object_materials(objects, texture_path, sod_materials):
    materials = set()
    for obj in objects:
        for mat in obj.data.materials:
            materials.add(mat)
    for mat in materials:
        finish_mat(mat, texture_path, sod_materials)