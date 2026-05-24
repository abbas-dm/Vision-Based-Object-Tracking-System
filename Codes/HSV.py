from picamera2 import Picamera2
import cv2
import numpy as np
import time

print("Starting Camera...")

picam2 = Picamera2()

picam2.configure(
    picam2.create_preview_configuration(
        main={
            "size": (640, 480),
            "format": "BGR888"
        }
    )
)

picam2.start()

time.sleep(2)

print("Point camera center to yellow ball")

try:

    while True:

        frame = picam2.capture_array()

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Center pixel
        center_pixel = hsv[240, 320]

        h = int(center_pixel[0])
        s = int(center_pixel[1])
        v = int(center_pixel[2])

        print(f"H:{h} S:{s} V:{v}")

        time.sleep(0.5)

except KeyboardInterrupt:

    print("Stopped")
