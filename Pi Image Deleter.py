import os
from time import sleep
from datetime import datetime, timezone
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
from picamera2 import Picamera2
import RPi.GPIO as GPIO

# Setup GPIO for Red LED
RED_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(RED_PIN, GPIO.OUT)

def set_led(state):
    GPIO.output(RED_PIN, state)

image_dir = "Image"
log_file = "upload_log.txt"

def capture_image():
    picam2 = Picamera2()
    config = picam2.create_still_configuration(main={"size": (1024, 768)})
    picam2.configure(config)
    picam2.start()
    sleep(3)

    today = datetime.now().strftime("%Y-%m-%d")
    image_folder = os.path.join(image_dir, today)
    os.makedirs(image_folder, exist_ok=True)  # Create the folder if it doesn't exist

    while True:
        try:
            # Turn on the Red LED for illumination
            set_led(GPIO.HIGH)
            sleep(1)  # Give some time for the LED to illuminate the scene

            # Capture image with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            image_path = os.path.join(image_folder, f"image_{timestamp}.jpg")
            picam2.capture_file(image_path)
            print(f"Image saved to {image_path}")

            # Turn off the Red LED after capturing the image
            set_led(GPIO.LOW)

            # Upload the captured image
            upload_image(image_path)

            # Sleep for 60 seconds before capturing the next image
            sleep(60)

        except (OSError, ValueError, RuntimeError) as error:
            log_error(f"Capture Error: {error}")
            sleep(5)
    picam2.stop()

def upload_image(file_path):
    location = {'latitude': 43.3554899, 'longitude': -80.3059555}  # Example coordinates
    device_id = "12345"
    device_datetime = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = "https://water-watch-58265eebffd9.herokuapp.com/upload/"
    boundary = "*****"

    # Preparing the data to be sent
    fields = {
        'latitude': str(location['latitude']),
        'longitude': str(location['longitude']),
        'deviceID': device_id,
        'device_datetime': device_datetime,
        'weather': "cloudy with chance of eclipse"
    }

    with open(file_path, 'rb') as file:
        fields['image'] = (os.path.basename(file_path), file, 'image/jpeg')
        m = MultipartEncoder(fields=fields, boundary=boundary)

        print(f"Uploading file: {file_path}")
        print(f"Data being sent: {fields}")

        try:
            response = requests.post(url, data=m, headers={'Content-Type': m.content_type})
            if response.status_code == 200:
                print("Upload Success!")
                log_success(file_path)
                delete_file(file_path)
            else:
                print(f"Upload Failed: {response.status_code} - {response.reason}")
                print(f"Response Text: {response.text}")
                print(f"Response Headers: {response.headers}")
                response.raise_for_status()
        except Exception as e:
            log_error(f"Upload Exception: {e}")

def delete_file(file_path):
    try:
        os.remove(file_path)
        print(f"Deleted file: {file_path}")
    except OSError as e:
        log_error(f"Error deleting file {file_path}: {e}")

def log_success(file_path):
    with open(log_file, 'a') as log:
        log.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Uploaded and deleted: {file_path}\n")

def log_error(error_message):
    with open(log_file, 'a') as log:
        log.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error: {error_message}\n")

if __name__ == "__main__":
    try:
        capture_image()
        print("Script has ended")
    except KeyboardInterrupt:
        GPIO.cleanup()  # Ensure GPIO pins are reset
        quit()
