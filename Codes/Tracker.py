from picamera2 import Picamera2
import cv2
import numpy as np
import gpiozero
import RPi.GPIO as GPIO
import time
from collections import deque

# =========================================================
# LOG FUNCTION
# =========================================================
def log(msg):
    print(f"[LOG] {time.strftime('%H:%M:%S')} - {msg}")


# =========================================================
# GPIO SETUP
# =========================================================
GPIO.setmode(GPIO.BCM)

TRIG = 6
ECHO = 5

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)


# =========================================================
# CAMERA SETUP
# =========================================================
log("Initializing camera...")

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

log("Camera started")


# =========================================================
# ROBOT SETUP
# =========================================================
robot = gpiozero.Robot(
    left=(22, 27),
    right=(17, 23)
)

log("Robot initialized")


# =========================================================
# DEBUG LED
# =========================================================
debug_led = gpiozero.LED(18)


# =========================================================
# IMAGE SETTINGS
# =========================================================
image_width = 640
center_image_x = image_width / 2


# =========================================================
# HSV RANGE FOR YOUR STRESS BALL
# =========================================================
# Calibrated from your real HSV values
lower_color = np.array([85, 180, 80])
upper_color = np.array([100, 255, 255])


# =========================================================
# DISTANCE SETTINGS
# =========================================================
SAFE_DISTANCE = 30      # cm
TOLERANCE = 3           # cm


# =========================================================
# SIMPLE P CONTROLLER
# =========================================================
Kp = 0.03


# =========================================================
# DISTANCE FILTER
# =========================================================
distance_buffer = deque(maxlen=5)


# =========================================================
# ULTRASONIC FUNCTION
# =========================================================
def get_distance():

    GPIO.output(TRIG, False)
    time.sleep(0.01)

    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    timeout = time.time() + 0.02

    pulse_start = time.time()
    pulse_end = time.time()

    # Wait for HIGH
    while GPIO.input(ECHO) == 0:

        pulse_start = time.time()

        if pulse_start > timeout:
            return 0

    # Wait for LOW
    while GPIO.input(ECHO) == 1:

        pulse_end = time.time()

        if pulse_end > timeout:
            return 0

    pulse_duration = pulse_end - pulse_start

    distance = pulse_duration * 17150

    return round(distance, 2)


# =========================================================
# FILTERED DISTANCE
# =========================================================
def get_filtered_distance():

    d = get_distance()

    if d == 0:
        return SAFE_DISTANCE

    distance_buffer.append(d)

    avg = sum(distance_buffer) / len(distance_buffer)

    return avg


# =========================================================
# SIMPLE PROPORTIONAL CONTROL
# =========================================================
def p_control(distance, target):

    error = distance - target

    output = Kp * error

    return output


# =========================================================
# MAIN LOOP
# =========================================================
try:

    while True:

        # -------------------------------------------------
        # CAPTURE CAMERA FRAME
        # -------------------------------------------------
        image = picam2.capture_array()

        # -------------------------------------------------
        # CONVERT TO HSV
        # -------------------------------------------------
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # -------------------------------------------------
        # CREATE MASK
        # -------------------------------------------------
        mask = cv2.inRange(
            hsv,
            lower_color,
            upper_color
        )

        # -------------------------------------------------
        # REMOVE NOISE
        # -------------------------------------------------
        mask = cv2.GaussianBlur(mask, (5, 5), 0)

        mask = cv2.erode(mask, None, iterations=1)

        mask = cv2.dilate(mask, None, iterations=2)

        # -------------------------------------------------
        # FIND CONTOURS
        # -------------------------------------------------
        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        object_area = 0
        object_x = 0

        # -------------------------------------------------
        # FIND LARGEST VALID OBJECT
        # -------------------------------------------------
        for contour in contours:

            area = cv2.contourArea(contour)

            # Ignore tiny noise
            if area < 150:
                continue

            x, y, w, h = cv2.boundingRect(contour)

            # Ignore thin/random shapes
            if w < 15 or h < 15:
                continue

            if area > object_area:

                object_area = area

                object_x = x + (w / 2)

        # -------------------------------------------------
        # DEBUG
        # -------------------------------------------------
        log(f"Object Area: {object_area}")

        # =================================================
        # TARGET FOUND
        # =================================================
        if object_area > 150:

            debug_led.on()

            # ---------------------------------------------
            # GET DISTANCE
            # ---------------------------------------------
            distance = get_filtered_distance()

            log(f"Distance: {distance:.2f} cm")

            # ---------------------------------------------
            # LEFT / RIGHT TRACKING
            # ---------------------------------------------
            if object_x > (center_image_x + 80):

                robot.right(0.5)

                log("Action: TURN RIGHT")

            elif object_x < (center_image_x - 80):

                robot.left(0.5)

                log("Action: TURN LEFT")

            else:

                # -----------------------------------------
                # DISTANCE CONTROL
                # -----------------------------------------
                control = p_control(
                    distance,
                    SAFE_DISTANCE
                )

                log(f"P Output: {control:.2f}")

                # -----------------------------------------
                # MAINTAIN DISTANCE
                # -----------------------------------------
                if abs(distance - SAFE_DISTANCE) <= TOLERANCE:

                    robot.stop()

                    log("Action: MAINTAIN DISTANCE")

                # -----------------------------------------
                # OBJECT FAR → MOVE FORWARD
                # -----------------------------------------
                elif control > 0:

                    speed = min(abs(control), 0.7)

                    robot.forward(speed)

                    log(f"Action: FORWARD | Speed: {speed:.2f}")

                # -----------------------------------------
                # OBJECT TOO CLOSE → MOVE BACKWARD
                # -----------------------------------------
                else:

                    speed = min(abs(control), 0.7)

                    robot.backward(speed)

                    log(f"Action: BACKWARD | Speed: {speed:.2f}")

        # =================================================
        # TARGET NOT FOUND
        # =================================================
        else:

            debug_led.off()

            robot.stop()

            log("Action: TARGET NOT FOUND")

        # Small delay
        time.sleep(0.05)


# =========================================================
# EXIT
# =========================================================
except KeyboardInterrupt:

    log("Stopping Robot")


# =========================================================
# CLEANUP
# =========================================================
finally:

    robot.stop()

    GPIO.cleanup()

    log("Program Closed")
