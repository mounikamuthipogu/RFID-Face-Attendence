import cv2
import face_recognition
import pickle
import time
import serial
import pandas as pd
import yagmail
import os
from datetime import datetime


# =========================================================
# EMAIL SETUP
# =========================================================

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
ALERT_EMAIL = os.getenv("ALERT_EMAIL")

if EMAIL_USER and EMAIL_PASSWORD:
    yag = yagmail.SMTP(EMAIL_USER, EMAIL_PASSWORD)
    print("[INFO] Email service configured.")
else:
    yag = None
    print("[WARNING] Email credentials are not configured.")


# =========================================================
# LOAD FACE ENCODINGS
# =========================================================

try:
    with open("encodings.pickle", "rb") as f:
        data = pickle.load(f)

    print("[INFO] Face encodings loaded successfully.")

except FileNotFoundError:
    print("[ERROR] encodings.pickle not found.")
    exit()


# =========================================================
# LOAD RFID - STUDENT MAPPING
# =========================================================

students_file = "students.csv"

try:
    students_df = pd.read_csv(students_file)

    # Create dictionary:
    # RFID -> Student Name
    rfid_students = dict(
        zip(
            students_df["RFID_ID"].astype(str),
            students_df["Name"].astype(str)
        )
    )

    print(
        f"[INFO] Loaded {len(rfid_students)} RFID students."
    )

except FileNotFoundError:
    print("[ERROR] students.csv not found.")
    exit()

except Exception as e:
    print(f"[ERROR] Failed to load students.csv: {e}")
    exit()


# =========================================================
# SERIAL / RFID SETUP
# =========================================================

try:
    ser = serial.Serial(
        "COM3",
        115200,
        timeout=1
    )

    time.sleep(2)

    print("[INFO] RFID serial connection established.")

except serial.SerialException as e:
    print(f"[ERROR] Could not open serial port: {e}")
    exit()


# =========================================================
# ATTENDANCE SETUP
# =========================================================

filename = "attendance.xlsx"

try:

    df = pd.read_excel(filename)

except FileNotFoundError:

    df = pd.DataFrame(
        columns=["Name", "Date", "Time"]
    )

    df.to_excel(
        filename,
        index=False
    )


# =========================================================
# DUPLICATE ATTENDANCE CHECK
# =========================================================

def already_attended(name):

    global df

    today = datetime.now().strftime("%Y-%m-%d")

    if df.empty:
        return False

    # Check whether same person already attended today
    result = df[
        (df["Name"].astype(str).str.lower() == name.lower())
        &
        (df["Date"].astype(str) == today)
    ]

    return not result.empty


# =========================================================
# ADD ATTENDANCE
# =========================================================

def add_attendance(name):

    global df

    # Prevent duplicate attendance
    if already_attended(name):

        print(
            f"[WARNING] {name} already marked "
            f"attendance today."
        )

        return

    now = datetime.now()

    date_now = now.strftime("%Y-%m-%d")
    time_now = now.strftime("%H:%M:%S")

    new_record = pd.DataFrame(
        [[name, date_now, time_now]],
        columns=["Name", "Date", "Time"]
    )

    df = pd.concat(
        [
            df,
            new_record
        ],
        ignore_index=True
    )

    df.to_excel(
        filename,
        index=False
    )

    print(
        f"[LOGGED] {name} | "
        f"{date_now} | {time_now}"
    )


# =========================================================
# FACE DETECTION + VERIFICATION
# =========================================================

def capture_and_detect(expected_name):

    print(
        f"[INFO] RFID verified for: "
        f"{expected_name}"
    )

    print("[INFO] Opening webcam...")

    vs = cv2.VideoCapture(0)

    if not vs.isOpened():

        print("[ERROR] Could not open webcam.")

        return

    time.sleep(2)

    ret, frame = vs.read()

    if not ret:

        print("[ERROR] Failed to capture frame.")

        vs.release()

        return


    # -----------------------------------------------------
    # Convert BGR to RGB
    # -----------------------------------------------------

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )


    # -----------------------------------------------------
    # Detect faces
    # -----------------------------------------------------

    boxes = face_recognition.face_locations(
        rgb
    )


    # -----------------------------------------------------
    # Generate face encodings
    # -----------------------------------------------------

    encodings = face_recognition.face_encodings(
        rgb,
        boxes
    )

    name = "Unknown"


    # =====================================================
    # FACE COMPARISON
    # =====================================================

    if encodings:

        matches = face_recognition.compare_faces(
            data["encodings"],
            encodings[0]
        )

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


    # =====================================================
    # RFID + FACE VERIFICATION
    # =====================================================

    if name.lower() == expected_name.lower():

        print(
            f"[SUCCESS] Face matched with "
            f"RFID identity: {name}"
        )

        # ---------------------------------------------
        # DUPLICATE ATTENDANCE CHECK
        # ---------------------------------------------

        if already_attended(name):

            print(
                f"[WARNING] {name} is already "
                f"marked present today."
            )

        else:

            add_attendance(name)


    else:

        print(
            "[ALERT] Unknown or mismatched "
            "face detected!"
        )


        # =================================================
        # SAVE PHOTO
        # =================================================

        photo_path = (
            f"unknown_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            f".jpg"
        )

        cv2.imwrite(
            photo_path,
            frame
        )

        print(
            f"[INFO] Photo saved: {photo_path}"
        )


        # =================================================
        # SEND EMAIL ALERT
        # =================================================

        if yag and ALERT_EMAIL:

            try:

                yag.send(
                    to=ALERT_EMAIL,
                    subject="Unknown Person Detected",
                    contents=(
                        "An unknown or mismatched "
                        "person was detected by the "
                        "RFID Face Attendance System.\n\n"
                        f"Expected Person: {expected_name}\n"
                        f"Detected Person: {name}\n"
                        f"Time: "
                        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    ),
                    attachments=photo_path
                )

                print(
                    "[INFO] Alert email sent."
                )

            except Exception as e:

                print(
                    f"[ERROR] Email failed: {e}"
                )

        else:

            print(
                "[WARNING] Email alert "
                "is not configured."
            )


    # -----------------------------------------------------
    # Release webcam
    # -----------------------------------------------------

    vs.release()

    cv2.destroyAllWindows()


# =========================================================
# MAIN RFID LOOP
# =========================================================

print(
    "[INFO] Waiting for RFID card..."
)

try:

    while True:

        if ser.in_waiting:

            try:

                code = (
                    ser.readline()
                    .decode(
                        "utf-8",
                        errors="ignore"
                    )
                    .strip()
                )

                print(
                    f"[RECEIVED RFID] {code}"
                )


                # =================================================
                # DYNAMIC RFID LOOKUP
                # =================================================

                if code in rfid_students:

                    expected_name = rfid_students[code]

                    print(
                        f"[INFO] RFID belongs to: "
                        f"{expected_name}"
                    )

                    capture_and_detect(
                        expected_name
                    )

                else:

                    print(
                        f"[WARNING] Unrecognized RFID: "
                        f"{code}"
                    )


            except Exception as e:

                print(
                    f"[ERROR] Failed to process "
                    f"RFID input: {e}"
                )


except KeyboardInterrupt:

    print(
        "\n[INFO] Program terminated by user."
    )

finally:

    ser.close()

    print(
        "[INFO] RFID connection closed."
    )
