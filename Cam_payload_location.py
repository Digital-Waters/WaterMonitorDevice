import os
from time import sleep
from datetime import datetime, timezone
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
from picamera2 import Picamera2

image_dir = "Image"

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
            # Capture image with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            image_path = os.path.join(image_folder, f"image_{timestamp}.jpg")
            picam2.capture_file(image_path)
            print(f"Image saved to {image_path}")

            # Upload the captured image
            upload_image(image_path)

            # Sleep for 60 seconds before capturing the next image
            sleep(60)

        except (OSError, ValueError, RuntimeError) as error:
            print(f"Error: {error}")
            sleep(5)
    picam2.stop()

def upload_image(file_path):
    location = {'latitude': 51.509865, 'longitude': -0.118092}
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
            else:
                print(f"Upload Failed: {response.status_code} - {response.reason}")
                print(f"Response Text: {response.text}")
                print(f"Response Headers: {response.headers}")
                response.raise_for_status()
        except Exception as e:
            print(f"Upload Exception: {e}")

if __name__ == "__main__":
    try:
        capture_image()
        print("Script has ended")
    except KeyboardInterrupt:
        quit()
