import face_recognition
import pickle
import os

known_faces_folder = "known_faces"

encodings = []
names = []

for filename in os.listdir(known_faces_folder):

    if filename.lower().endswith((".jpg", ".jpeg", ".png")):

        image_path = os.path.join(
            known_faces_folder,
            filename
        )

        image = face_recognition.load_image_file(image_path)

        face_encodings = face_recognition.face_encodings(image)

        if len(face_encodings) == 0:
            print(f"[WARNING] No face found in {filename}")
            continue

        encoding = face_encodings[0]

        name = os.path.splitext(filename)[0].lower()

        encodings.append(encoding)
        names.append(name)

        print(f"[INFO] Encoded: {name}")

data = {
    "encodings": encodings,
    "names": names
}

with open("encodings.pickle", "wb") as f:
    pickle.dump(data, f)

print("[SUCCESS] encodings.pickle created successfully!")