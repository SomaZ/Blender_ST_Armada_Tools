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

        sod = SOD.from_file_path(sanitized_filepath)
        mesh_objects = Blender_SOD.ImportSOD(sod)
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
        obj = bpy.context.active_object

        addon_name = __name__.split('.')[0]
        prefs = context.preferences.addons[addon_name].preferences

        if obj is None:
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
        row.prop(obj, '["node_type"]')
        # Add operators to change node type

        if "animated" in obj:
            layout.separator()
            row = layout.row()
            row.prop(obj, '["animated"]', text = "Animated")
            if obj["animated"]:
                row = layout.row()
                row.prop(obj, '["start_frame"]', text = "First frame")
                row = layout.row()
                row.prop(obj, '["end_frame"]', text = "Last frame")
                row = layout.row()
                row.prop(obj, '["length"]', text = "Length")
        else:
            # Add animation info operator
            pass
        
        layout.separator()
        
        if node_type == 12:
            row = layout.row()
            row.prop(obj, '["emitter"]')
            return
        
        mesh_props = ("Material", "Texture")
        for prop in mesh_props:
            if prop.lower() not in obj:
                continue
            row = layout.row()
            row.prop(obj, '["' + prop.lower() + '"]')

        cull_match = {
            0: "Two sided",
            1: "Front sided"
        }
        if "cull_type" in obj:
            row = layout.row()
            if obj["cull_type"] not in cull_match:
                row.label(text = "Unknown cull type")
            else:
                row.label(text = cull_match[obj["cull_type"]])
            row.prop(obj, '["cull_type"]')
        else:
            # Add cull info operator
            pass

        layout.separator()

        row = layout.row()
        if "texture_animation" in obj:
            row.prop(obj, '["texture_animation"]', text = "Animated texture")
        else:
            # Add animation info operator
            return

        if not obj["texture_animation"]:
            return
        
        row = layout.row()
        if "ref_animation" in obj:
            row.prop(obj, '["ref_animation"]', text = "Animation")

        row = layout.row()
        if "ref_type" in obj:
            row.label(text = "Animation type: " + str(obj["ref_type"]))

        row = layout.row()
        if "ref_offset" in obj:
            row.prop(obj, '["ref_offset"]', text = "Offset")

