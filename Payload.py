import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import os
from datetime import datetime, timezone

def upload_photo(location, device_id, file_path, device_datetime):
    url = "https://water-watch-58265eebffd9.herokuapp.com/upload/"
    boundary = "*****"
    
    # Preparing the data to be sent
    fields = {
        'latitude': str(location['latitude']) if location else "30.234293742",
        'longitude': str(location['longitude']) if location else "-148.2378468222",
        'deviceID': device_id,
        'device_datetime': device_datetime,
        'weather': "cloudy with chance of eclipse"
    }

    # Adding the image file to the fields
    with open(file_path, 'rb') as file:
        fields['image'] = (os.path.basename(file_path), file, 'image/jpeg')
        
        # Creating a MultipartEncoder
        m = MultipartEncoder(fields=fields, boundary=boundary)

        # Debugging information
        print(f"Uploading file: {file_path}")
        print(f"Data being sent: {fields}")

        # Sending the request
        try:
            response = requests.post(url, data=m, headers={'Content-Type': m.content_type})
            if response.status_code == 200:
                print("Upload Success!")
            else:
                print(f"Upload Failed: {response.status_code} - {response.reason}")
                print(f"Response Text: {response.text}")
                print(f"Response Headers: {response.headers}")
                response.raise_for_status()  # Raise an error for bad status codes
        except Exception as e:
            print(f"Upload Exception: {e}")

# Example usage
location = {'latitude': 51.509865, 'longitude': -0.118092}
device_id = "12345"
photos_directory = "/home/anjana/DIgitalWaterWarden/Image/2024-07-17"

if __name__ == "__main__":
    files = os.listdir(photos_directory)
    
    for file_name in files:
        file_path = os.path.join(photos_directory, file_name)
        
        # Check if the file is an image (you can add more extensions if needed)
        if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            # Use ISO 8601 format with timezone (UTC)
            device_datetime = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            upload_photo(location, device_id, file_path, device_datetime)
    print("Script has ended")
