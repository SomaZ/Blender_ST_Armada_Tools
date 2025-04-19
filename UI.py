import bpy
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty
from bpy.types import PropertyGroup
from .SOD import SOD
from . import Blender_SOD
from . import Blender_Materials

def guess_texture_path(file_path):
    SPLIT_FOLDER = "/sod/"
    split = file_path.split(SPLIT_FOLDER)
    if len(split) > 1:
        return split[0]+"/textures/rgb/"
    return None

class Import_STA_SOD(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.sta_sod"
    bl_label = "Import Star Trek Armada SOD (.sod)"
    filename_ext = ".sod"
    filter_glob: StringProperty(default="*.sod", options={'HIDDEN'})

    filepath: StringProperty(
        name="File Path",
        description="File path used for importing the SOD file",
        maxlen=1024,
        default="")

    def execute(self, context):
        sanitized_filepath = self.filepath.replace("\\", "/")
        context.scene.sta_sod_file_path = sanitized_filepath

        try:
            sod = SOD.from_file_path(sanitized_filepath)
        except Exception as e:
            print(e)
            self.report({"ERROR"}, str(e))
            return {'CANCELLED'}
        mesh_objects = Blender_SOD.Import_SOD(sod)
        texture_path = guess_texture_path(sanitized_filepath.lower())
        Blender_Materials.finsh_object_materials(mesh_objects, texture_path, sod.materials)
        
        return {'FINISHED'}


class Export_STA_SOD(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.sta_sod"
    bl_label = "Export Star Trek Armada SOD (.sod)"
    filename_ext = ".sod"
    filter_glob: StringProperty(default="*.sod", options={'HIDDEN'})

    filepath: StringProperty(
        name="File Path",
        description="File path used for exporting the SOD file",
        maxlen=1024,
        default="")
    only_selected: BoolProperty(
        name="Export only selected",
        description="Exports only selected Objects",
        default=False)
    preset: EnumProperty(
        name="Surfaces",
        description="You can select wether you want to export per object "
        "or merged based on materials.",
        default='MATERIALS',
        items=[
            ('MATERIALS', "From Materials",
             "Merges surfaces based on materials. Supports multi "
             "material objects", 0),
            ('OBJECTS', "From Objects",
             "Simply export objects. There will be no optimization", 1),
        ])

    def execute(self, context):
        objects = context.scene.objects
        if self.only_selected:
            objects = context.selected_objects

        Blender_SOD.Export_SOD(self.filepath)

        status = (True, "Whatever")
        if status[0]:
            return {'FINISHED'}
        else:
            self.report({"ERROR"}, status[1])
            return {'CANCELLED'}

def menu_func_sod_import(self, context):
    self.layout.operator(Import_STA_SOD.bl_idname, text="ST:Armada (.sod)")

def menu_func_sod_export(self, context):
    self.layout.operator(Export_STA_SOD.bl_idname, text="ST:Armada (.sod)")

def update_material_type(self, context):
    obj = context.active_object
    obj["material"] = self.material_type
    return

def update_face_cull(self, context):
    obj = context.active_object
    obj["cull_type"] = int(self.face_cull)
    return

def update_animated(self, context):
    obj = context.active_object
    if self.animated:
        if "start_frame" not in obj:
            obj["start_frame"] = 1
        if "end_frame" not in obj:
            obj["end_frame"] = 1
        if "length" not in obj:
            obj["length"] = 4.0
    else:
        if "start_frame" in obj:
            del obj["start_frame"]
        if "end_frame" in obj:
            del obj["end_frame"]
        if "length" in obj:
            del obj["length"]

def update_texture_animation(self, context):
    obj = context.active_object
    if self.texture_animated:
        if "ref_animation" not in obj:
            obj["ref_animation"] = ""
        if "ref_type" not in obj:
            obj["ref_type"] = 4
        if "ref_offset" not in obj:
            obj["ref_offset"] = 0.0
    else:
        if "ref_animation" in obj:
            del obj["ref_animation"]
        if "ref_type" in obj:
            del obj["ref_type"]
        if "ref_offset" in obj:
            del obj["ref_offset"]

class STA_Dynamic_Node_Properties(PropertyGroup):
    material_type: EnumProperty(
        name="Material Type",
        description="Changes how the models material behave",
        default='default',
        #update=update_material_type,
        items=[
            ('default', "Standard material",
             "Standard material", 0),
            ('additive', "Use additive blending",
             "Use additive blending", 1),
            ('translucent', "Semi transparent",
             "Semi transparent", 2),
            ('alphathreshold', "Use alpha channel 'cut outs'",
             "alpha channels will have hard edged 'threshold' but"
              " objects will be drawn quickly", 3),
            ('alpha ', "Use entire alpha channel",
             "Object will require sorting, so will have performance implications", 4),
            ('wireframe', "Use wireframe graphics",
             "Use wireframe graphics", 5),
            ('wormhole', "Used by wormholes",
             "Used by wormholes", 6),
        ])
    face_cull: EnumProperty(
        name="Face Culling",
        description="Changes how the models faces orient",
        default="1",
        #update=update_face_cull,
        items=[
            ("1", "Front sided",
             "Backface culling", 0),
            ("0", "Two sided",
             "No face culling", 1),
        ])
    texture_name: StringProperty(
        name="Mesh Texture",
        description="Changes the models texture",
        default="default"
    )
    animated: BoolProperty(
        name="Animated Node",
        description="Is the current node animated?",
        default=False,
        update=update_animated
    )
    texture_animated: BoolProperty(
        name="Texture animation",
        description="Is the current texture animated?",
        default=False,
        update=update_texture_animation
    )


class STA_PT_Materialpanel(bpy.types.Panel):
    bl_idname = "STA_PT_Materialpanel"
    bl_label = "ST: Armada Material"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"

    def draw(self, context):
        layout = self.layout
        mat = context.material
        if mat is None:
            return
        
        if "ST:A Material" not in mat.node_tree.nodes:
            # Add material operator with name input
            return

        material_node = mat.node_tree.nodes["ST:A Material"]

        layout.label(text = material_node.node_tree.name)
        if material_node is not None:
            col = layout.column()
            ambient = material_node.inputs["Ambient Color"]
            col.prop(ambient, "default_value", text="Ambient Color")
            diffuse = material_node.inputs["Diffuse Color"]
            col.prop(diffuse, "default_value", text="Diffuse Color")
            specular = material_node.inputs["Specular Color"]
            col.prop(specular, "default_value", text="Specular Color")
            specular = material_node.inputs["Specular Power"]
            col.prop(specular, "default_value", text="Specular Power")
            model = material_node.inputs["Lighting Model"]
            col.prop(model, "default_value", text="Lighting Model")


class STA_PT_EntityPanel(bpy.types.Panel):
    bl_idname = "STA_PT_entity_panel"
    bl_label = "Selected Node"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ST: Armada"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        addon_name = __name__.split('.')[0]
        prefs = context.preferences.addons[addon_name].preferences

        if obj is None:
            return
        if obj.type not in ("MESH", "EMPTY"):
            return
        
        node_type = 0
        if "node_type" in obj:
            node_type = obj["node_type"]
        elif obj.type == "MESH":
            node_type = 1
        elif "emitter" in obj:
            node_type = 12

        node_match = {
            0: "Null",
            1: "Mesh",
            3: "Sprite",
            11: "LOD control",
            12: "Emitter"
        }

        row = layout.row()
        if node_type not in node_match:
            row.label(text = "Unknown node type")
            row.prop(obj, '["node_type"]')
            return

        row.label(text = node_match[node_type])
        #row.prop(obj, '["node_type"]')
        # Add operators to change node type
        layout.separator()
        layout.prop(obj.sta_dynamic_props, "animated")
        if obj.sta_dynamic_props.animated:
            if "start_frame" in obj:
                row = layout.row()
                row.prop(obj, '["start_frame"]', text = "First frame")
            if "end_frame" in obj: 
                row = layout.row()
                row.prop(obj, '["end_frame"]', text = "Last frame")
            if "length" in obj:
                row = layout.row()
                row.prop(obj, '["length"]', text = "Length")
        
        layout.separator()
        if node_type == 12:
            row = layout.row()
            row.prop(obj, '["emitter"]')
            return
        if node_type == 1:
            layout.prop(obj.sta_dynamic_props, "material_type")
            layout.prop(obj.sta_dynamic_props, "face_cull")
            layout.prop(obj.sta_dynamic_props, "texture_name")

        layout.separator()
        layout.prop(obj.sta_dynamic_props, "texture_animated")
        if obj.sta_dynamic_props.texture_animated:
            if "ref_animation" in obj:
                row = layout.row()
                row.prop(obj, '["ref_animation"]', text = "Animation")

            if "ref_type" in obj:
                row = layout.row()
                row.label(text = "Animation type: " + str(obj["ref_type"]))

            if "ref_offset" in obj:
                row = layout.row()
                row.prop(obj, '["ref_offset"]', text = "Offset")

