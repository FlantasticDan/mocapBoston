import bpy
import pickle
import sys
import os

C = bpy.context
D = bpy.data
# find solver file
filepath = C.blend_data.filepath
filepath = filepath.split("\\")
filePath = ""
for x in range(0, len(filepath) - 1):
    filePath = filePath + filepath[x] + "\\"

with open(os.path.join(filePath, "solve.mocap"), "rb") as data:
    markers = pickle.load(data)

end = len(markers)
C.scene.frame_start = 0
C.scene.frame_end = end - 1
frame = 0

while frame < end:
    for point in markers[frame]:
        try:
            obj = D.objects[point[0]]
        except KeyError:
            continue
        obj.location = point[1]
        obj.keyframe_insert(data_path="location", frame=frame)
    frame += 1