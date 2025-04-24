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
    "version": (0, 9, 0),
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

    normal_map_option: bpy.props.EnumProperty(
        name="Normal Map Import",
        description="Choose whether to import normal maps and what format to expect",
        default="DirectX",
        items=[
            ("OpenGL", "OpenGL",
             "Import normal maps in OpenGL format", 0),
            ("DirectX", "DirectX",
             "Import normal maps in DirectX format", 1),
            ("Skip", "Skip",
             "Skip normal map import", 2)
        ]
    )

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "normal_map_option")

classes = (STAAddonPreferences,
           UI.STA_Dynamic_Node_Properties,
           UI.Import_STA_SOD,
           UI.Export_STA_SOD,
           UI.STA_OP_UpdateMaterials,
           UI.STA_PT_Materialpanel,
           UI.STA_OP_ChangeNodeType,
           UI.STA_PT_EntityPanel,
           UI.STA_OP_Toggle_Material_Export,
           UI.STA_OP_Make_Material,
           UI.STA_OP_Delete_Material,
           UI.STA_PT_MaterialExportPanel,
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
    
    addon_name = __name__.split('.')[0]
    prefs = bpy.context.preferences.addons[addon_name].preferences

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(UI.menu_func_sod_import)
    bpy.types.TOPBAR_MT_file_export.remove(UI.menu_func_sod_export)
    del bpy.types.Scene.sta_sod_file_path
    del bpy.types.Object.sta_dynamic_props
    for cls in classes:
        bpy.utils.unregister_class(cls)
    

if __name__ == "__main__":
    register()