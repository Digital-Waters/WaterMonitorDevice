from datetime import datetime
from time import sleep
from PIL import Image
import os
import logging

_camera_available = False
picam2 = None
GPIO = None
PIN17 = 17
imageDir = "images"

try:
    from picamera2 import Picamera2
    from libcamera import controls
    import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN17, GPIO.OUT)
    picam2 = Picamera2()
    picam2.configure(picam2.create_still_configuration())
    _camera_available = True
except Exception as _e:
    pass  # Camera hardware or libraries not available on this device


def setLED(state):
    if not _camera_available:
        return
    try:
        GPIO.output(PIN17, state)
    except (OSError, ValueError, RuntimeError) as error:
        log.error(f"In setLED(). GPIO Error: {error}")


def captureCameraImage(log, deviceID):
    if not _camera_available:
        log.warning("In captureCameraImage(). Camera is not available on this device. Uploading null image.")
        return None

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
            imagePath = os.path.join(imageFolder, f"{deviceID}_{timestamp}.jpg")
            picam2.capture_file(imagePath)
            log.info(f"In captureCameraImage(). Image saved to {imagePath}")

            # Uncomment for smaller rez image focused on center.
            cropImage(imagePath)

            # Turn off the Red LED after capturing the image
            setLED(GPIO.LOW)

        except (OSError, ValueError, RuntimeError) as error:
            log.error(f"In captureCameraImage(). Error saving image: {error}")
            return None

        finally:
            picam2.stop()
            return str(imagePath)

    except (RuntimeError, Exception) as error:
        log.error(f"In captureCameraImage(). Error initializing or using the camera: {error}")
        return None


# Crop image, best used for fixed-focus lenses, to give a 'digital zoom'
def cropImage(imgPath):
    image = Image.open(imgPath)

    # Make square image, trim sides.
    width, height = image.size
    left = (width - height) * 0.5
    top = 0
    right = width - left
    bottom = height

    # Crop the image
    cropped_image = image.crop((left, top, right, bottom))

    # Save the cropped image, overwritting original
    cropped_image.save(imgPath)


# Set exposure, gain, and other controls. See cameraTester.py for testing image outputs
def configureLowLightSettings():

    # Longer exposure time, higher gain for low-light
    picam2.set_controls({
        #"AwbEnable": True,
        "AwbEnable": False,
        #"AwbMode": 1,
        #"ColourGains": (2.0, 1.0),
        "ExposureTime": 75000
        #"AnalogueGain": 5.0
    })
