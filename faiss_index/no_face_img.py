import os
import pickle

if os.path.exists("image_mapping.pkl"):
    with open("image_mapping.pkl", "rb") as f:
        no_face_set = pickle.load(f)
        print("exists")
    if isinstance(no_face_set, dict):
        no_face_set = set(no_face_set.keys())

else:
    no_face_set = set()

print(len(no_face_set))
