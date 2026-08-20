import serial
import time

try:
    ser = serial.Serial("COM3", 115200, timeout=1)
    time.sleep(2)
    print("RFID serial connection established.")
except serial.SerialException as e:
    print(f"Could not open serial port: {e}")
    exit()

print("Waiting for RFID card...")

try:
    while True:
        if ser.in_waiting:
            code = ser.readline().decode(
                "utf-8",
                errors="ignore"
            ).strip()

            print(f"Received: {code}")

            if code == "A":
                capture_and_detect("mounika")
            elif code == "B":
                capture_and_detect("sasi")
            else:
                print(f"Unrecognized RFID code: {code}")

except KeyboardInterrupt:
    print("Program terminated.")
    ser.close()
