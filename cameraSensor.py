from picamera2 import Picamera2
from datetime import datetime
from time import sleep
import os
import logging
import RPi.GPIO as GPIO
from libcamera import controls
from PIL import Image


# Setup GPIO for Red LED
RED_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(RED_PIN, GPIO.OUT)
picam2 = Picamera2()
imageDir = "Image"
picam2.configure(picam2.create_still_configuration()) #capture full resolution photo


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

        # Uncomment for cameras with motorized lenses (not fixed-focus).
        #setFocus(log) 

        today = datetime.now().strftime("%Y-%m-%d")
        imageFolder = os.path.join(imageDir, today)
        os.makedirs(imageFolder, exist_ok=True)  # Create the folder if it doesn't exist

        try:
            # Turn on the Red LED for illumination
            setLED(GPIO.HIGH)
            sleep(1)  # Give some time for the LED to illuminate the scene

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            imagePath = os.path.join(imageFolder, f"image_{timestamp}.jpg")
            picam2.capture_file(imagePath)
            log.info(f"In captureCameraImage(). Image saved to {imagePath}")
            
            # Uncomment for fixed-focus lenses 
            cropImage(imagePath)
            
            # Turn off the Red LED after capturing the image
            setLED(GPIO.LOW)

        except (OSError, ValueError, RuntimeError) as error:
            log.error(f"In captureCameraImage(). Error saving image: {error}")
            return False


        finally:
            picam2.stop()
            return str(imagePath) 

    except (RuntimeError, Exception) as error:
        log.error(f"In captureCameraImage(). Error initializing or using the camera: {error}")
        return False


# Set the focus position. Not used with fixed-focus lens (here in case we change cameras)
def setFocus(log):
    try:
        focus_position = 0.5  # Adjust this value based on experimentation
        picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": focus_position})

    except (OSError, ValueError, RuntimeError) as error:
        log.error(f"In setFocus(): {error}")


# Crop image, best used for fixed-focus lenses, to give a 'digital zoom'
def cropImage(imgPath):
    image = Image.open(imgPath)

    # Calculate the cropping box (for ~45% of the central area)
    width, height = image.size
    left = width * 0.3
    top = height * 0.25
    right = width * 0.7
    bottom = height * 0.75

    # Crop the image
    cropped_image = image.crop((left, top, right, bottom))

    # Save the cropped image, overwritting original
    cropped_image.save(imgPath)
