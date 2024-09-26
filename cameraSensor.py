from picamera2 import Picamera2
from datetime import datetime
from time import sleep
from libcamera import controls
from PIL import Image
import os
import logging
import RPi.GPIO as GPIO


# Setup GPIO for LED activation
PIN17 = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN17, GPIO.OUT)
picam2 = Picamera2()
imageDir = "Image"
picam2.configure(picam2.create_still_configuration()) #capture full resolution photo


def setLED(state):
    try:
        GPIO.output(PIN17, state)
    except (OSError, ValueError, RuntimeError) as error:
        log.error(f"In setLED(). GPIO Error: {error}")

    
def captureCameraImage(log, deviceID):
    try:
        log.info(f"In captureCameraImage().")
        picam2.start()
        configureLowLightSettings()

        today = datetime.now().strftime("%Y-%m-%d")
        imageFolder = os.path.join(imageDir, today)
        os.makedirs(imageFolder, exist_ok=True)  # Create the folder if it doesn't exist

        try:
            # Turn on the Red LED for illumination
            setLED(GPIO.HIGH)
            sleep(2)  # Give some time for the LED to illuminate the scene

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            imagePath = os.path.join(imageFolder, f"{timestamp}__{deviceID}.jpg")
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


# Set exposure, gain, and other controls. See cameraTester.py for testing image outputs
def configureLowLightSettings():

    # Longer exposure time, higher gain for low-light
    picam2.set_controls({
        "AwbEnable": False,
        #"AwbMode": 1,
        #"ColourGains": (2.0, 1.0),
        "ExposureTime": 75000
        #"AnalogueGain": 5.0  
    })
