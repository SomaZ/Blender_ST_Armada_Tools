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
    else:
        split = file_path.split("/textures/rgb/")
        if len(split) > 1:
            return split[0]+"/textures/rgb/"
        else:
            addon_name = __name__.split('.')[0]
            prefs = bpy.context.preferences.addons[addon_name].preferences
            if prefs.default_image_path != "":
                return prefs.default_image_path
    return ""


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
        items=[
            ('default', "Standard material",
             "Standard material", 0),
            ('additive', "Additive blending",
             "Use additive blending", 1),
            ('translucent', "Semi transparent",
             "Semi transparent", 2),
            ('alphathreshold', "Alpha channel 'cut outs'",
             "alpha channels will have hard edged 'threshold' but"
              " objects will be drawn quickly", 3),
            ('alpha', "Alpha blend",
             "Object will require sorting, so will have performance implications", 4),
            ('wireframe', "Wireframe",
             "Use wireframe graphics", 5),
            ('wormhole', "Wormhole",
             "Used by wormholes", 6),
        ])
    face_cull: EnumProperty(
        name="Face Culling",
        description="Changes how the models faces orient",
        default="1",
        items=[
            ("1", "Front sided",
             "Backface culling", 0),
            ("0", "Two sided",
             "No face culling", 1),
        ])
    texture_name: StringProperty(
        name="Mesh Texture",
        description="Changes the models texture",
        default=""
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


class STA_OP_UpdateMaterial(bpy.types.Operator):
    """Update Blender material"""
    bl_idname = "sta.update_material"
    bl_label = "Material update"
    bl_options = {"UNDO", "INTERNAL", "REGISTER"}
    name: StringProperty()

    def execute(self, context):
        obj = context.object
        mat = context.material

        if not mat.use_nodes:
            print("No nodes in material found")
            return {'CANCELLED'}
        
        if "ST:A Material" not in mat.node_tree.nodes:
            print("No ST:A Material found")
            return {'CANCELLED'}
        
        material_name = self.name
        new_mat_name = "{}.{}.{}.{}".format(
            material_name,
            obj.sta_dynamic_props.texture_name,
            obj.sta_dynamic_props.face_cull,
            obj.sta_dynamic_props.material_type
        )
        if new_mat_name in bpy.data.materials:
            re_mat = bpy.data.materials[new_mat_name]
            if re_mat.use_nodes and re_mat.node_tree.nodes.get("ST:A Material"):
                for slot in obj.material_slots:
                    if mat.name == slot.material.name:
                        slot.material = bpy.data.materials[new_mat_name]
                return {'FINISHED'}
        
        #create new mat when texture name or face_cull or type is different
        material_data = mat.name.split(".")
        if len(material_data) >= 4:
            _, current_texture, current_cull, current_type = material_data[:4]
            if (current_texture != obj.sta_dynamic_props.texture_name or
                 current_cull != obj.sta_dynamic_props.face_cull or
                 current_type != obj.sta_dynamic_props.material_type):
                new_mat = bpy.data.materials.new(new_mat_name)
                new_mat.use_nodes = True
                for slot in obj.material_slots:
                    if mat.name == slot.material.name:
                        slot.material = bpy.data.materials[new_mat_name]
                mat = new_mat

        mat.name = new_mat_name
        texture_path = ""
        if context.scene.sta_sod_file_path != "":
            texture_path = guess_texture_path(context.scene.sta_sod_file_path.lower())

        img_node = None
        for node in mat.node_tree.nodes:
            if node.type != "TEX_IMAGE":
                continue
            img_node = node
            break
    
        mat_node = mat.node_tree.nodes.get("ST:A Material")
        Blender_Materials.finish_mat(mat, texture_path, [], img_node, mat_node)

        return {'FINISHED'}


class STA_OP_Make_Material(bpy.types.Operator):
    """Create new material"""
    bl_idname = "sta.make_material"
    bl_label = "New"
    bl_options = {"UNDO", "INTERNAL", "REGISTER"}

    def execute(self, context):
        obj = context.object
        mat = context.material

        if not mat.use_nodes:
            mat.use_nodes = True
        img_node = None
        for node in mat.node_tree.nodes:
            if node.type != "TEX_IMAGE":
                continue
            img_node = node
            break
        if img_node is not None:
            if obj.sta_dynamic_props.texture_name == "":
                obj.sta_dynamic_props.texture_name = img_node.image.name.split(".")[0]

        new_mat_name = "{}.{}.{}.{}".format(
            mat.name.split(".")[0],
            obj.sta_dynamic_props.texture_name,
            obj.sta_dynamic_props.face_cull,
            obj.sta_dynamic_props.material_type
        )
        make_new_material = True
        if new_mat_name in bpy.data.materials:
            re_mat = bpy.data.materials[new_mat_name]
            if re_mat.use_nodes and re_mat.node_tree.nodes.get("ST:A Material"):
                for slot in obj.material_slots:
                    if mat.name == slot.material.name:
                        slot.material = bpy.data.materials[new_mat_name]
                return {'FINISHED'}
            make_new_material = False
        
        if make_new_material:
            new_mat = bpy.data.materials.new(new_mat_name)
        else:
            new_mat = mat
            new_mat.name = new_mat_name
        new_mat.use_nodes = True
        for slot in obj.material_slots:
            if mat.name == slot.material.name:
                slot.material = new_mat
        texture_path = ""
        if context.scene.sta_sod_file_path != "":
            texture_path = guess_texture_path(context.scene.sta_sod_file_path.lower())

        Blender_Materials.finish_mat(new_mat, texture_path, [])
        if "ST:A Material" not in new_mat.node_tree.nodes:
            return {'FINISHED'}
        mat_nt = new_mat.node_tree.nodes["ST:A Material"].node_tree
        if "ST:A_Export" in mat_nt.nodes:
            mat_nt.nodes["ST:A_Export"].outputs[0].default_value = 1.0

        return {'FINISHED'}


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
            layout.operator("sta.make_material", text="Make new material")
            return

        material_node = mat.node_tree.nodes["ST:A Material"]

        row = layout.row()
        row.prop(material_node.node_tree, "name", text = "")
        row = row.row()
        row.ui_units_x = 1
        row.operator("sta.update_material", text="", icon="CHECKMARK").name = material_node.node_tree.name
        if material_node is not None:
            col = layout.column()
            if bpy.app.version >= (4, 0, 0):
                ambient = material_node.node_tree.interface.items_tree["Ambient Color"]
                col.prop(ambient, "default_value", text="Ambient Color")
                diffuse = material_node.node_tree.interface.items_tree["Diffuse Color"]
                col.prop(diffuse, "default_value", text="Diffuse Color")
                specular = material_node.node_tree.interface.items_tree["Specular Color"]
                col.prop(specular, "default_value", text="Specular Color")
                specular = material_node.node_tree.interface.items_tree["Specular Power"]
                col.prop(specular, "default_value", text="Specular Power")
                model = material_node.node_tree.interface.items_tree["Lighting Model"]
                col.prop(model, "default_value", text="Lighting Model")
            else:
                ambient = material_node.node_tree.inputs["Ambient Color"]
                col.prop(ambient, "default_value", text="Ambient Color")
                diffuse = material_node.node_tree.inputs["Diffuse Color"]
                col.prop(diffuse, "default_value", text="Diffuse Color")
                specular = material_node.node_tree.inputs["Specular Color"]
                col.prop(specular, "default_value", text="Specular Color")
                specular = material_node.node_tree.inputs["Specular Power"]
                col.prop(specular, "default_value", text="Specular Power")
                model = material_node.node_tree.inputs["Lighting Model"]
                col.prop(model, "default_value", text="Lighting Model")


class STA_OP_ChangeNodeType(bpy.types.Operator):
    """Changes node type"""
    bl_idname = "sta.change_node_type"
    bl_label = "Change"
    bl_options = {"UNDO", "INTERNAL", "REGISTER"}
    node_type: IntProperty()

    def execute(self, context):
        obj = context.object
        if self.node_type == 12 and "emitter" not in obj:
            obj["emitter"] = ""
        obj["node_type"] = self.node_type
        return {'FINISHED'}
    

def update_object_materials(obj, context):
    texture_path = guess_texture_path(context.scene.sta_sod_file_path.lower())
    materials = set()
    for mat in obj.data.materials:
        materials.add(mat)
    for mat in materials:
        new_mat_name = "{}.{}.{}.{}".format(
            mat.name.split(".")[0],
            obj.sta_dynamic_props.texture_name,
            obj.sta_dynamic_props.face_cull,
            obj.sta_dynamic_props.material_type
        )
        if new_mat_name in bpy.data.materials:
            for slot in obj.material_slots:
                if mat.name == slot.material.name:
                    slot.material = bpy.data.materials[new_mat_name]
            continue

        new_mat = bpy.data.materials.new(new_mat_name)
        new_mat.use_nodes = True
        for slot in obj.material_slots:
            if mat.name == slot.material.name:
                slot.material = new_mat
        Blender_Materials.finish_mat(new_mat, texture_path, [])
    return


class STA_OP_UpdateObjectMaterials(bpy.types.Operator):
    """Updates all object materials"""
    bl_idname = "sta.udpate_all_object_materials"
    bl_label = "Update materials"
    bl_options = {"UNDO", "INTERNAL", "REGISTER"}

    def execute(self, context):
        update_object_materials(context.object, context)
        return {'FINISHED'}


class STA_OP_LoadMeshTexture(bpy.types.Operator):
    """Loads an image and sets the meshes material textures"""
    bl_idname = "sta.load_mesh_texture"
    bl_label = "Load new texture"
    bl_options = {"UNDO", "INTERNAL", "REGISTER"}
    filepath: StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE'})
    filename_ext = ".tga"
    filter_glob: StringProperty(default="*.tga", options={'HIDDEN'})
    directory: StringProperty()

    def execute(self, context):
        sanitized_path = self.filepath.replace("\\", "/")
        texture = sanitized_path.rsplit("/", 1)[1]
        if texture.lower().endswith(".tga"):
            texture = texture[:-len(".tga")]
        obj = context.object
        obj.sta_dynamic_props.texture_name = texture
        if context.scene.sta_sod_file_path == "":
            context.scene.sta_sod_file_path = sanitized_path

        update_object_materials(obj, context)

        return {'FINISHED'}
    
    def invoke(self, context, event):
        addon_name = __name__.split('.')[0]
        prefs = context.preferences.addons[addon_name].preferences

        texture_path = guess_texture_path(context.scene.sta_sod_file_path.lower())
        if texture_path != "":
            self.directory = texture_path

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class STA_PT_EntityPanel(bpy.types.Panel):
    bl_idname = "STA_PT_entity_panel"
    bl_label = "Selected Node"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ST: Armada"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

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
        if node_type == 0 or node_type == 11:
            row.operator("sta.change_node_type", text = "Make Sprite").node_type = 3
            row.operator("sta.change_node_type", text = "Make Emitter").node_type = 12
        elif node_type == 3:
            row.operator("sta.change_node_type", text = "Make Null").node_type = 0
            row.operator("sta.change_node_type", text = "Make Emitter").node_type = 12
        elif node_type == 12:
            row.operator("sta.change_node_type", text = "Make Sprite").node_type = 3
            row.operator("sta.change_node_type", text = "Make Null").node_type = 0

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
        if node_type != 1:
            return
        layout.prop(obj.sta_dynamic_props, "material_type")
        layout.prop(obj.sta_dynamic_props, "face_cull")
        layout.prop(obj.sta_dynamic_props, "texture_name")
        row = layout.row()
        row.operator("sta.udpate_all_object_materials")
        row.operator("sta.load_mesh_texture")

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


class STA_OP_Toggle_Material_Export(bpy.types.Operator):
    """Toggles material export"""
    bl_idname = "sta.toggle_material_export"
    bl_label = "Toggle Export"
    bl_options = {"UNDO", "INTERNAL", "REGISTER"}
    name: StringProperty()

    def execute(self, context):
        node_group = bpy.data.node_groups[self.name]
        on = node_group.nodes["ST:A_Export"].outputs[0].default_value > 0
        if on:
            node_group.nodes["ST:A_Export"].outputs[0].default_value = 0.0
        else:
            node_group.nodes["ST:A_Export"].outputs[0].default_value = 1.0
        return {'FINISHED'}


class STA_OP_Delete_Material(bpy.types.Operator):
    """Delete unused Material"""
    bl_idname = "sta.delete_material"
    bl_label = "Delete"
    bl_options = {"UNDO", "INTERNAL", "REGISTER"}
    name: StringProperty()

    def execute(self, context):
        bpy.data.node_groups.remove(
            bpy.data.node_groups[self.name])
        return {'FINISHED'}


class STA_PT_MaterialExportPanel(bpy.types.Panel):
    bl_idname = "STA_PT_material_export_panel"
    bl_label = "Material Export"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ST: Armada"

    def draw(self, context):
        layout = self.layout

        for node_group in bpy.data.node_groups:
            row = layout.row()
            if not node_group.nodes or "ST:A_Export" not in node_group.nodes:
                continue
            export_status = node_group.nodes["ST:A_Export"].outputs[0].default_value > 0.0
            users = row.row()
            users.label(text = "[{}]".format(node_group.users))
            users.ui_units_x = 1
            row.prop(node_group, "name", text = "", icon = "CHECKMARK" if export_status else "X")
            row = row.row()
            row.ui_units_x = 10
            row.operator(
                "sta.toggle_material_export", text="Toggle Export").name = node_group.name
            if node_group.users == 0:
                row.operator(
                    "sta.delete_material", text="", icon="X").name = node_group.name


STA_NODES = (
    "root", "Geometry", "Hardpoints", "Lights",
    "Damage", "Borg", "Crew", "Engines", "Life",
    "Sensors", "Shield", "Target"
    )


class STA_OP_Create_default_rig(bpy.types.Operator):
    """Creates a default SOD rig"""
    bl_idname = "sta.create_rig"
    bl_label = "Create default rig"
    bl_options = {"UNDO", "INTERNAL", "REGISTER"}

    def execute(self, context):
        parenting = {
            "Geometry": "root",
            "Damage": "root",
            "Hardpoints": "root",
            "Lights": "root",
            "Geometry": "root",
            "Borg": "Damage",
            "Crew": "Damage",
            "Engines": "Damage",
            "Life": "Damage",
            "Sensors": "Damage",
            "Shield": "Damage",
            "Target": "Damage"
        }
        for node in STA_NODES:
            if node in context.scene.objects:
                continue
            bpy.ops.object.empty_add(type="ARROWS")
            obj = context.object
            obj.name = node
        for p in parenting:
            if p not in context.scene.objects:
                if p.lower() not in context.scene.objects:
                    print("Couldn't find parent", p)
                    continue
                context.scene.objects[p.lower()].name = p
            if parenting[p] not in context.scene.objects:
                if parenting[p].lower() not in context.scene.objects:
                    print("Couldn't find node to parent", parenting[p])
                    continue
                context.scene.objects[parenting[p].lower()].name = parenting[p]
            context.scene.objects[p].parent = context.scene.objects[parenting[p]]
        return {'FINISHED'}
    

class STA_OP_Parent_to(bpy.types.Operator):
    """Parent selected objects to node"""
    bl_idname = "sta.parent_to"
    bl_label = "Parent"
    bl_options = {"UNDO", "INTERNAL", "REGISTER"}
    parent: StringProperty()

    def execute(self, context):
        if self.parent not in context.scene.objects:
            if self.parent.lower() not in context.scene.objects:
                return {'CANCELLED'}
            parent = context.scene.objects[self.parent.lower()]
        else:
            parent = context.scene.objects[self.parent]
        selected_objs = context.selected_objects
        for obj in selected_objs:
            mat = obj.matrix_world.copy()
            obj.parent = parent
            obj.matrix_world = mat
        return {'FINISHED'}


class STA_PT_HelperPanel(bpy.types.Panel):
    bl_idname = "STA_PT_helper_panel"
    bl_label = "Helpers"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ST: Armada"

    def draw(self, context):
        layout = self.layout
        
        if "root" not in context.scene.objects:
            layout.operator("sta.create_rig")

        for node in STA_NODES[1:]:
            if node == "Damage" and node in context.scene.objects:
                layout.label(text="Damage Nodes:")
                continue
            node_name = node
            if node not in context.scene.objects:
                if node.lower() not in context.scene.objects:
                    continue
                node_name = node.lower()
            if context.scene.objects[node_name].type != "EMPTY":
                layout.label(text="{} is not a valid Node (Maybe an object?)".format(node_name))
                continue
            layout.operator("sta.parent_to", text="Parent to {}".format(node)).parent = node
