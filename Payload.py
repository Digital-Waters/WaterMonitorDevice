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
                log.error(f"Response Headers: {response.headers}")
                if fromFile == False:
                    savePayload(payloadData)
        except Exception as e:
            log.error(f"Upload Exception: {e}")
            savePayload(payloadData)  # Save the payload in case of failure


def savePayload(payload):
    folder = "payload"
    filename = os.path.join(folder, "payloadData.txt")

    os.makedirs(folder, exist_ok=True)

    try:
        logs = []
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            with open(filename, 'r') as f:
                try:
                    logs = json.load(f)
                    if not isinstance(logs, list):
                        logs = [logs]
                except json.JSONDecodeError:
                    logs = []
        else:
            logs = []

        # Append new data to the logs
        logs.append(payload)

        # Save the updated logs back to the file
        with open(filename, 'w') as f:
            json.dump(logs, f, indent=4)

    except Exception as e:
        print(f"Error saving payload: {e}")  # Handle any file I/O exceptions


def uploadSavedPayloads(log, secrets):
    folder = "payload"
    filename = os.path.join(folder, "payloadData.txt")

    # Check if file exists and has data
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        with open(filename, 'r') as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []

        # Upload each saved payload one by one
        if logs:
            updated_logs = []
            for payload in logs:
                try:
                    # Try to re-upload saved payload
                    uploadPayload(payload, log, secrets, fromFile=True)
                except Exception as e:
                    log.error(f"Failed to upload saved payload: {e}")
                    # Add the payload back to the updated list if the upload fails
                    updated_logs.append(payload)

            # Write the remaining failed payloads back to the file
            with open(filename, 'w') as f:
                json.dump(updated_logs, f, indent=4)

            if not updated_logs:
                log.info("All saved payloads successfully uploaded.")
        else:
            log.info("No saved payloads to upload.")
