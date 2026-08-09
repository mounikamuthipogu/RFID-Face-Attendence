import cv2
import face_recognition
import pickle
import pandas as pd
from datetime import datetime


# ==============================
# LOAD FACE ENCODINGS
# ==============================

try:
    with open("encodings.pickle", "rb") as f:
        data = pickle.load(f)

    print("[INFO] Face encodings loaded successfully.")

except FileNotFoundError:
    print("[ERROR] encodings.pickle not found.")
    exit()


# ==============================
# ATTENDANCE FILE
# ==============================

filename = "attendance.xlsx"

try:
    df = pd.read_excel(filename)

except FileNotFoundError:
    df = pd.DataFrame(columns=["Name", "Time"])
    df.to_excel(filename, index=False)


# ==============================
# ADD ATTENDANCE
# ==============================

def add_attendance(name):

    global df

    time_now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [[name, time_now]],
                columns=["Name", "Time"]
            )
        ],
        ignore_index=True
    )

    df.to_excel(filename, index=False)

    print(f"[ATTENDANCE] {name} - {time_now}")


# ==============================
# FACE RECOGNITION
# ==============================

print("[INFO] Starting camera...")
print("[INFO] Press Q to quit.")


video = cv2.VideoCapture(0)

if not video.isOpened():
    print("[ERROR] Camera could not be opened.")
    exit()


while True:

    ret, frame = video.read()

    if not ret:
        print("[ERROR] Could not read camera.")
        break

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    face_locations = face_recognition.face_locations(rgb)

    face_encodings = face_recognition.face_encodings(
        rgb,
        face_locations
    )

    for face_encoding, face_location in zip(
        face_encodings,
        face_locations
    ):

        matches = face_recognition.compare_faces(
            data["encodings"],
            face_encoding,
            tolerance=0.5
        )

        name = "Unknown"

        if True in matches:

            matched_indices = [
                i
                for i, match in enumerate(matches)
                if match
            ]

            counts = {}

            for i in matched_indices:

                person_name = data["names"][i]

                counts[person_name] = (
                    counts.get(person_name, 0) + 1
                )

            name = max(
                counts,
                key=counts.get
            )

            add_attendance(name)

        else:
            print("[ALERT] Unknown face detected.")

        # Face box
        top, right, bottom, left = face_location

        cv2.rectangle(
            frame,
            (left, top),
            (right, bottom),
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            name,
            (left, top - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )


    cv2.imshow(
        "RFID Face Attendance",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


video.release()
cv2.destroyAllWindows()

print("[INFO] Program terminated.")