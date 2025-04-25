from __future__ import annotations
import bpy

def create_node_output(node_group, type, name):
    if bpy.app.version >= (4, 0, 0):
        node_group.interface.new_socket(name=name, in_out='OUTPUT', socket_type=type)
    else:
        node_group.outputs.new(type, name)

def create_node_input(node_group, type, name):
    if bpy.app.version >= (4, 0, 0):
        node_group.interface.new_socket(name=name, in_out='INPUT', socket_type=type)
    else:
        node_group.inputs.new(type, name)

def set_default_input(node_group, name, value):
    if bpy.app.version >= (4, 0, 0):
        node_group.interface.items_tree[name].default_value = value
    else:
        node_group.inputs[name].default_value = value

def set_default_output(node_group, name, value):
    if bpy.app.version >= (4, 0, 0):
        node_group.interface.items_tree[name].default_value = value
    else:
        node_group.outputs[name].default_value = value

class Generic_Node_Group():
    name = ""

    @classmethod
    def get_node_tree(self, variable):
        if self.name == "":
            node_tree = bpy.data.node_groups.get(variable)
        else:
            node_tree = bpy.data.node_groups.get(self.name)

        if node_tree is None:
            return self.create_node_tree(variable)
        else:
            return node_tree

    @classmethod
    def create_node_tree(self, variable):
        raise NotImplementedError
    
class Material_Node(Generic_Node_Group):
    @classmethod
    def create_node_tree(self, material_name) -> Material_Node:
        material_group = bpy.data.node_groups.new(material_name, 'ShaderNodeTree')

        group_inputs = material_group.nodes.new('NodeGroupInput')
        group_inputs.location = (-1600, 0)
        create_node_input(material_group, 'NodeSocketColor', 'Texture Color')
        create_node_input(material_group, 'NodeSocketFloat', 'Texture Alpha')
        create_node_input(material_group, 'NodeSocketColor', 'Ambient Color')
        create_node_input(material_group, 'NodeSocketColor', 'Diffuse Color')
        create_node_input(material_group, 'NodeSocketColor', 'Specular Color')
        create_node_input(material_group, 'NodeSocketFloat', 'Specular Power')
        create_node_input(material_group, 'NodeSocketInt', 'Lighting Model')

        group_outputs = material_group.nodes.new('NodeGroupOutput')
        group_outputs.location = (1300, 0)
        create_node_output(material_group, 'NodeSocketColor', 'Color')
        create_node_output(material_group, 'NodeSocketFloat', 'Alpha')

        node_add = material_group.nodes.new(type="ShaderNodeMixRGB")
        node_add.name = "Term1"
        node_add.blend_type = "ADD"
        node_add.inputs[0].default_value = 1.0
        node_add.location = (26.8, -269.7)
        material_group.links.new(
            group_inputs.outputs["Ambient Color"], node_add.inputs["Color1"])
        material_group.links.new(
            group_inputs.outputs["Diffuse Color"], node_add.inputs["Color2"])
        
        node_inv_gamma = material_group.nodes.new(type="ShaderNodeGamma")
        node_inv_gamma.inputs["Gamma"].default_value = .454545
        node_inv_gamma.location = (239.8, 0)
        material_group.links.new(
            group_inputs.outputs["Texture Color"], node_inv_gamma.inputs["Color"])

        node_mult = material_group.nodes.new(type="ShaderNodeMixRGB")
        node_mult.name = "Term2"
        node_mult.blend_type = "MULTIPLY"
        node_mult.inputs[0].default_value = 1.0
        node_mult.location = (800, -300)
        material_group.links.new(
            node_add.outputs["Color"], node_mult.inputs["Color2"])
        material_group.links.new(
            node_inv_gamma.outputs["Color"], node_mult.inputs["Color1"])
        
        geometry = material_group.nodes.new("ShaderNodeNewGeometry")
        geometry.name = "Geometry"

        #node Vector Math
        vector_math = material_group.nodes.new("ShaderNodeVectorMath")
        vector_math.name = "Vector Math"
        vector_math.operation = 'DOT_PRODUCT'

        #node Math
        math = material_group.nodes.new("ShaderNodeMath")
        math.name = "Math"
        math.operation = 'POWER'
        math.use_clamp = True

        #node Term1.001
        term1_001 = material_group.nodes.new("ShaderNodeMixRGB")
        term1_001.name = "Term1.001"
        term1_001.blend_type = 'MULTIPLY'
        term1_001.use_alpha = False
        term1_001.use_clamp = True
        #Fac
        term1_001.inputs[0].default_value = 1.0

        #node Term1.002
        term1_002 = material_group.nodes.new("ShaderNodeMixRGB")
        term1_002.name = "Term1.002"
        term1_002.blend_type = 'ADD'
        term1_002.use_alpha = False
        term1_002.use_clamp = True
        #Fac
        term1_002.inputs[0].default_value = 1.0

        #node Vector Math.001
        vector_math_001 = material_group.nodes.new("ShaderNodeVectorMath")
        vector_math_001.name = "Vector Math.001"
        vector_math_001.operation = 'ADD'

        #node Vector Math.002
        vector_math_002 = material_group.nodes.new("ShaderNodeVectorMath")
        vector_math_002.name = "Vector Math.002"
        vector_math_002.operation = 'NORMALIZE'

        #node Vector Math.003
        vector_math_003 = material_group.nodes.new("ShaderNodeVectorMath")
        vector_math_003.name = "Vector Math.003"
        vector_math_003.operation = 'DOT_PRODUCT'

        #node Math.001
        math_001 = material_group.nodes.new("ShaderNodeMath")
        math_001.name = "Math.001"
        math_001.operation = 'GREATER_THAN'
        math_001.use_clamp = False
        #Value_001
        math_001.inputs[1].default_value = 1.1

        #node Term2.001
        term2_001 = material_group.nodes.new("ShaderNodeMixRGB")
        term2_001.name = "Term2.001"
        term2_001.blend_type = 'MIX'
        term2_001.use_alpha = False
        term2_001.use_clamp = False

        gamma = material_group.nodes.new(type="ShaderNodeGamma")
        gamma.inputs["Gamma"].default_value = 2.2
        gamma.location = (1129, -74.5)

        math_002 = material_group.nodes.new("ShaderNodeMath")
        math_002.name = "Math.002"
        math_002.operation = 'GREATER_THAN'
        #Value_001
        math_002.inputs[1].default_value = 0.1

        #node Term2.002
        term2_002 = material_group.nodes.new("ShaderNodeMixRGB")
        term2_002.name = "Term2.002"
        term2_002.blend_type = 'MIX'
        term2_002.use_alpha = False
        term2_002.use_clamp = False

        #Set locations
        group_inputs.location = (-1227.2, -33.9)
        group_outputs.location = (1390, 40.5)
        node_add.location = (239.8, -287.4)
        node_mult.location = (528.6, -126.1)
        geometry.location = (-1217, -496.9)
        vector_math.location = (-658.4, -610.1)
        math.location = (-17.7, -623.2)
        term1_001.location = (236, -480.8)
        term1_002.location = (724.9, -324.6)
        vector_math_001.location = (-882.7, -691.2)
        vector_math_002.location = (-879.3, -830.6)
        vector_math_003.location = (-43.3, -236.7)
        math_001.location = (537.5, 158.3)
        term2_001.location = (929, -74.5)
        math_002.location = (-204, -87)
        term2_002.location = (240, -107)

        material_group.links.new(group_inputs.outputs[1], group_outputs.inputs[1])
        material_group.links.new(group_inputs.outputs[2], node_add.inputs[1])
        material_group.links.new(group_inputs.outputs[3], node_add.inputs[2])
        material_group.links.new(geometry.outputs[1], vector_math.inputs[0])
        material_group.links.new(group_inputs.outputs[5], math.inputs[1])
        material_group.links.new(group_inputs.outputs[4], term1_001.inputs[1])
        material_group.links.new(math.outputs[0], term1_001.inputs[2])
        material_group.links.new(geometry.outputs[1], vector_math_001.inputs[0])
        material_group.links.new(vector_math_001.outputs[0], vector_math_002.inputs[0])
        material_group.links.new(geometry.outputs[1], vector_math_003.inputs[0])
        material_group.links.new(geometry.outputs[4], vector_math_003.inputs[1])
        material_group.links.new(vector_math_003.outputs[1], node_add.inputs[0])
        material_group.links.new(geometry.outputs[4], vector_math_001.inputs[1])
        material_group.links.new(group_inputs.outputs[6], math_001.inputs[0])
        material_group.links.new(node_mult.outputs[0], term1_002.inputs[1])
        material_group.links.new(vector_math_002.outputs[0], vector_math.inputs[1])
        material_group.links.new(term1_002.outputs[0], term2_001.inputs[2])
        material_group.links.new(node_mult.outputs[0], term2_001.inputs[1])
        material_group.links.new(math_001.outputs[0], term2_001.inputs[0])
        material_group.links.new(term2_001.outputs[0], gamma.inputs[0])
        material_group.links.new(gamma.outputs[0], group_outputs.inputs[0])
        material_group.links.new(vector_math.outputs[1], math.inputs[0])
        material_group.links.new(term1_001.outputs[0], term1_002.inputs[2])
        material_group.links.new(group_inputs.outputs[6], math_002.inputs[0])
        material_group.links.new(math_002.outputs[0], term2_002.inputs[0])
        material_group.links.new(group_inputs.outputs[3], term2_002.inputs[1])
        material_group.links.new(node_add.outputs[0], term2_002.inputs[2])
        material_group.links.new(term2_002.outputs[0], node_mult.inputs[2])
        export_node = material_group.nodes.new(type="ShaderNodeValue")
        export_node.name = "ST:A_Export"
        export_node.outputs[0].default_value = 0
        export_node.location = (-1220.9, 72.6)

        set_default_input(material_group, "Texture Color", [1.0, 1.0, 1.0, 1.0])
        set_default_input(material_group, "Texture Alpha", 1.0)
        set_default_input(material_group, "Diffuse Color", [1.0, 1.0, 1.0, 1.0])
        set_default_input(material_group, "Ambient Color", [0.2, 0.2, 0.2, 1.0])
        set_default_input(material_group, "Specular Color", [0.45, 0.45, 0.45, 1.0])
        set_default_input(material_group, "Specular Power", 50.0)
        
        return material_group