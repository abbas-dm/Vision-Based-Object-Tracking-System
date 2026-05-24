from picamera2 import Picamera2
import cv2
import numpy as np
import time

print("Starting Camera...")

picam2 = Picamera2()

picam2.configure(
    picam2.create_preview_configuration(
        main={"size": (640, 480), "format": "BGR888"}
    )
)

picam2.start()

time.sleep(2)

print("Camera Started")

# =====================================================
# YOUR ACTUAL BALL COLOR
# =====================================================
lower_color = np.array([85, 180, 80])
upper_color = np.array([100, 255, 255])

try:

    while True:

        # ------------------------------------------------
        # Capture frame
        # ------------------------------------------------
        frame = picam2.capture_array()

        # ------------------------------------------------
        # Convert to HSV
        # ------------------------------------------------
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # ------------------------------------------------
        # Create mask
        # ------------------------------------------------
        mask = cv2.inRange(
            hsv,
            lower_color,
            upper_color
        )

        # ------------------------------------------------
        # Noise removal
        # ------------------------------------------------
        mask = cv2.GaussianBlur(mask, (5, 5), 0)

        mask = cv2.erode(mask, None, iterations=1)

        mask = cv2.dilate(mask, None, iterations=2)

        # ------------------------------------------------
        # Find contours
        # ------------------------------------------------
        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        detected = False

        for contour in contours:

            area = cv2.contourArea(contour)

            if area > 150:

                detected = True

                print("BALL DETECTED")
                print(f"Area: {area}")

                break

        if not detected:

            print("No Ball")

        time.sleep(0.1)

except KeyboardInterrupt:

    print("Stopped")
