from picamera2 import Picamera2
from datetime import datetime
from time import sleep
import os
import logging

image_dir = "Image"
log = logging.getLogger('DWLogger')
log.propagate = False

def captureCameraImage():
    try:
        log.info(f"In captureCameraImage().")
        picam2 = Picamera2()
        config = picam2.create_still_configuration(main={"size": (1024, 768)})
        picam2.configure(config)
        picam2.start()
        sleep(3)

        today = datetime.now().strftime("%Y-%m-%d")
        image_folder = os.path.join(image_dir, today)
        os.makedirs(image_folder, exist_ok=True)  # Create the folder if it doesn't exist

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            image_path = os.path.join(image_folder, f"image_{timestamp}.jpg")
            picam2.capture_file(image_path)
            log.info(f"In captureCameraImage(). Image saved to {image_path}")

        except (OSError, ValueError, RuntimeError) as error:
            log.error(f"In captureCameraImage(). Error saving image: {error}")

        finally:
            picam2.stop()

    except (RuntimeError, Exception) as error:
        log.error(f"In captureCameraImage(). Error initializing or using the camera: {error}")