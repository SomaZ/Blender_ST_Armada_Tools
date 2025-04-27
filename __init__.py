# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


bl_info = {
    "name": "Star Trek Armada Tools",
    "author": "SomaZ",
    "version": (0, 9, 9),
    "description": "Importer/Exporter for Star Trek Armada sod files",
    "blender": (4, 1, 0),
    "location": "File > Import-Export",
    "warning": "",
    "category": "Import-Export"
}

if "bpy" in locals():
    # Just do all the reloading here
    import importlib
    from . import SOD, Blender_SOD
    importlib.reload(SOD)
    importlib.reload(Blender_SOD)
    from . import Blender_Material_Nodes
    importlib.reload(Blender_Material_Nodes)
    from . import Blender_Materials
    importlib.reload(Blender_Materials)
    from . import UI
    importlib.reload(UI)
else:
    import bpy
    from . import UI

# ------------------------------------------------------------------------
#    store properties in the user preferences
# ------------------------------------------------------------------------
class STAAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    default_image_path: bpy.props.StringProperty(
        name="Default image path",
        description="Folder to look for images",
        default="",
        subtype="DIR_PATH",
        maxlen=2048,
    )

    default_export_game: bpy.props.EnumProperty(
        name="Default export game",
        description="Export for Armada or Armada II",
        default='1.8',
        items=[
            ('1.8', "Star Trek: Armada",
             "Default to SOD version 1.8", 0),
            ('1.93', "Star Trek: Armada II",
             "Default to SOD version 1.93", 1),
        ])

    def assetslibs_list_cb(self, context):
        if bpy.app.version >= (3, 0, 0):
            libs = context.preferences.filepaths.asset_libraries
            return [(lib.path, lib.name, "")
                    for lib in libs]
        else:
            return []

    assetlibrary: bpy.props.EnumProperty(
        items=assetslibs_list_cb,
        name="Asset Library",
        description="Asset library to use for storing sprites and emitters"
    )

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "default_image_path")
        row = layout.row()
        row.prop(self, "default_export_game")
        if bpy.app.version < (3, 0, 0):
            return
        layout.separator()
        row = layout.row()
        row.prop(self, "assetlibrary")
        row.operator("sta.fill_asset_lib", text="Fill with sprites and emitters")


classes = (UI.STA_OP_FillAssetLibrary,
           STAAddonPreferences,
           UI.STA_Dynamic_Node_Properties,
           UI.Import_STA_SOD,
           UI.Export_STA_SOD,
           UI.STA_OP_UpdateMaterial,
           UI.STA_PT_Materialpanel,
           UI.STA_OP_UpdateObjectMaterials,
           UI.STA_OP_LoadMeshTexture,
           UI.STA_OP_ChangeNodeType,
           UI.STA_PT_EntityPanel,
           UI.STA_OP_Toggle_Material_Export,
           UI.STA_OP_Make_Material,
           UI.STA_OP_Delete_Material,
           UI.STA_PT_MaterialExportPanel,
           UI.STA_OP_Create_default_rig,
           UI.STA_OP_Parent_to,
           UI.STA_PT_HelperPanel,
           )


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(UI.menu_func_sod_import)
    bpy.types.TOPBAR_MT_file_export.append(UI.menu_func_sod_export)
    bpy.types.Object.sta_dynamic_props = bpy.props.PointerProperty(
        type=UI.STA_Dynamic_Node_Properties)

    bpy.types.Scene.sta_sod_file_path = bpy.props.StringProperty(
        name="ST: Armada SOD file path",
        description="Full path to the last imported sod File")


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(UI.menu_func_sod_import)
    bpy.types.TOPBAR_MT_file_export.remove(UI.menu_func_sod_export)
    del bpy.types.Scene.sta_sod_file_path
    del bpy.types.Object.sta_dynamic_props
    for cls in classes:
        bpy.utils.unregister_class(cls)
    

if __name__ == "__main__":
    register()
