import bpy
import mathutils
import sys

# Creates individual designs in the design space from the base design.
# Parameters are (nose forward displacement, nose vertical displacement), in meters

max_disp_y = 1
max_disp_z = 1
min_disp_y = -1
min_disp_z = -1

def export_model(params, export_path='./model.obj'):
    scene = bpy.context.scene
    # find deformation cage
    deformation = scene.objects['Deformation']
    verts = deformation.data.vertices

    # select vertices on top front
    for vert in verts:
        if vert.co.y > 2.4 and vert.co.z > 1.3:
            # deform
            vert.co.y += min(max(float(params[0]), min_disp_y), max_disp_y)
            vert.co.z += min(max(float(params[1]), min_disp_z), max_disp_z)

    # select objects to export
    to_export = ["Charger", "Wheel"]
    for object in scene.objects:
        object.select_set(object.name in to_export)

    # export
    bpy.ops.export_scene.obj(filepath=export_path, check_existing=False, use_selection=True,axis_forward='-X',axis_up='Z')
    # save .blend file
    bpy.ops.wm.save_as_mainfile(filepath='./assets/edited.blend')
    

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index("--") + 1 :]
    export_model(argv[:2], argv[2])