from picamera2 import Picamera2
from datetime import datetime
from time import sleep
import os
import logging
import RPi.GPIO as GPIO

# Setup GPIO for Red LED
RED_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(RED_PIN, GPIO.OUT)
picam2 = Picamera2()
image_dir = "Image"
config = picam2.create_still_configuration(main={"size": (1024, 1024)})
picam2.configure(config)

def setLED(state):
    try:
        GPIO.output(RED_PIN, state)
    except (OSError, ValueError, RuntimeError) as error:
        log.error(f"In setLED(). GPIO Error: {error}")

    
def captureCameraImage(log):
    try:
        log.info(f"In captureCameraImage().")
                
        picam2.start()
        sleep(3)

        today = datetime.now().strftime("%Y-%m-%d")
        image_folder = os.path.join(image_dir, today)
        os.makedirs(image_folder, exist_ok=True)  # Create the folder if it doesn't exist

        try:
            # Turn on the Red LED for illumination
            setLED(GPIO.HIGH)
            sleep(1)  # Give some time for the LED to illuminate the scene

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            image_path = os.path.join(image_folder, f"image_{timestamp}.jpg")
            picam2.capture_file(image_path)
            log.info(f"In captureCameraImage(). Image saved to {image_path}")

            # Turn off the Red LED after capturing the image
            setLED(GPIO.LOW)

        except (OSError, ValueError, RuntimeError) as error:
            log.error(f"In captureCameraImage(). Error saving image: {error}")

        finally:
            picam2.stop()

    except (RuntimeError, Exception) as error:
        log.error(f"In captureCameraImage(). Error initializing or using the camera: {error}")
