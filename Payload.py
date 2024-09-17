import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import os
from datetime import datetime, timezone
import json

def uploadPayload(payloadData, log, secrets, fromFile):
    url = secrets["apiURL"]
    apiKey = secrets["apiKey"]
    boundary = "*****"

    # Get the device ID from the payload data
    deviceId = payloadData.get('deviceID', "UNKNOWN")  # Use UNKNOWN if deviceID not found

    latitude = str(payloadData.get('latitude', "999"))
    longitude = str(payloadData.get('longitude', "999"))
    dateTime = payloadData.get('dateTime', datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    # Preparing the data to be sent
    fields = {
        'latitude': latitude,
        'longitude': longitude,
        'deviceID': deviceId,  # Include the dynamic device ID here
        'device_datetime': dateTime,
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

                # After success, attempt to upload saved payloads
                if fromFile == False:
                    uploadSavedPayloads(log, secrets)
            else:
                log.error(f"Upload Failed: {response.status_code} - {response.reason}")
                log.error(f"Response Text: {response.text}")
                #log.error(f"Response Headers: {response.headers}")
                if fromFile == False:
                    savePayload(payloadData, log)
        except Exception as e:
            log.error(f"Upload Exception: {e}")
            savePayload(payloadData)  # Save the payload in case of failure


def savePayload(payload, log):
    folder = "payload"
    filename = os.path.join(folder, "payloadData.txt")

    os.makedirs(folder, exist_ok=True)

    try:
        with open(filename, 'a') as f:
            f.write(json.dumps(payload) + '\n')
        log.info("Payload data wrote to file")
    except Exception as e:
        log.error(f"Error saving payload: {e}")  


def uploadSavedPayloads(log, secrets):
    folder = "payload"
    filename = os.path.join(folder, "payloadData.txt")
    
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            logs = [json.loads(line.strip()) for line in f.readlines()]

        # Iterate over logs and try to upload each one
        for payload in logs[:]:
            try:
                # Try to upload the payload
                uploadPayload(payload, log, secrets, fromFile=True)
                log.info(f"Payload uploaded successfully: {payload['deviceID']}")

                # If upload is successful, remove it from the logs
                logs.remove(payload)

                # Overwrite the file with the remaining failed payloads after each success
                with open(filename, 'w') as f:
                    for remaining_payload in logs:
                        f.write(json.dumps(remaining_payload) + '\n')

            except Exception as e:
                log.error(f"Failed to upload saved payload: {e}")
        
        # Check if all payloads were uploaded
        if not logs:
            log.info("All saved payloads successfully uploaded.")
        else:
            log.error("Some payloads could not be uploaded, saved in the file.")
    else:
        log.info("No saved payloads to upload.")
