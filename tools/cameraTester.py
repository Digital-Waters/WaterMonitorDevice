from picamera2 import Picamera2
from time import sleep
import os
from datetime import datetime
import RPi.GPIO as GPIO
from libcamera import controls
from PIL import Image


# Initialize Picamera2
picam2 = Picamera2()

# Configure for still image capture (full resolution)
picam2.configure(picam2.create_still_configuration())

PIN17 = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN17, GPIO.OUT)

def testCameraSettings():

    # Create directory to store images
    testImageDir = "TestImage"
    today = datetime.now().strftime("%Y-%m-%d")
    imageFolder = os.path.join(testImageDir, today)
    os.makedirs(imageFolder, exist_ok=True)

    # Define ranges and intervals for settings
    exposure_times = [200000,500000,800000,1000000]
    analogue_gains = [3.0,4.0,5.0,6.0,8.0,10.0] 
    mode_values = [1]#[0,1,2,3,4,5,6,7]

    picam2.start()

    # Cycle through combinations
    for exposure_time in exposure_times:
        for analogue_gain in analogue_gains:
        	for mode_value in mode_values:
	            # Set camera controls for this combination
	            picam2.set_controls({
	                "AwbEnable": True,
	                "AwbMode": mode_value,
	                "ExposureTime": exposure_time,
	                "AnalogueGain": analogue_gain
	            })
	            
	            setLED(GPIO.HIGH)
	            sleep(2)
	            
	            # Capture the image
	            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
	            image_filename = f"image_{timestamp}_ET{exposure_time}_AG{analogue_gain}_AWBM{mode_value}.jpg"
	            image_path = os.path.join(imageFolder, image_filename)
	            picam2.capture_file(image_path)
	            print(f"Captured image with ExposureTime={exposure_time}, AnalogueGain={analogue_gain}, AWBMode={mode_value}")

	            setLED(GPIO.LOW)
	            cropImage(image_path)
	            # Brief pause to avoid overwhelming the system
	            sleep(5)

    print("Image capturing for all combinations is complete.")
    picam2.stop()

def setLED(state):
    try:
        GPIO.output(PIN17, state)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"In setLED(). GPIO Error: {error}")


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

# UNUSED. Set the focus position. Not used with fixed-focus lens (here in case we change cameras)
def setFocus():
    try:
        focus_position = 0.5  # Adjust this value based on experimentation
        picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": focus_position})

    except (OSError, ValueError, RuntimeError) as error:
        print(f"In setFocus(): {error}")


def getCamControlsList():
	# Query and print all available controls
	available_controls = picam2.camera_controls
	for control, details in available_controls.items():
	    print(f"{control}: {details}")

if __name__ == "__main__":
    #getCamControlsList()
    testCameraSettings()