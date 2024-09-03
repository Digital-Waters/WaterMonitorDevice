import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import os
from datetime import datetime, timezone

def upload_photo(payloadData, log):
    url = "https://water-watch-58265eebffd9.herokuapp.com/upload/"
    boundary = "*****"
    deviceId = "12345"
    
    # Preparing the data to be sent
    fields = {
        'latitude': str(payloadData['latitude']),
        'longitude': str(payloadData['longitude']),
        'deviceID': deviceId,
        'device_datetime': payloadData["dateTime"],
        'weather': "cloudy with chance of eclipse"
    }

    currDirectory = os.path.dirname(os.path.abspath(__file__))

    filePath = os.path.join(currDirectory, payloadData["image"])
    # Adding the image file to the fields
    with open(filePath, 'rb') as file:
        fields['image'] = (os.path.basename(filePath), file, 'image/jpeg')
        
        # Creating a MultipartEncoder
        m = MultipartEncoder(fields=fields, boundary=boundary)

        # Debugging information
        log.info(f"Uploading file: {filePath}")
        log.info(f"Data being sent: {fields}")

        # Sending the request
        try:
            response = requests.post(url, data=m, headers={'Content-Type': m.content_type})
            if response.status_code == 200:
                log.info("Successfully uploaded payload to DB")
            else:
                log.error(f"Upload Failed: {response.status_code} - {response.reason}")
                log.error(f"Response Text: {response.text}")
                log.error(f"Response Headers: {response.headers}")
                response.raise_for_status()  # Raise an error for bad status codes
        except Exception as e:
            log.error(f"Upload Exception: {e}")

