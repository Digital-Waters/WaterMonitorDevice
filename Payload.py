import requests
import os
import json
import subprocess
from requests_toolbelt.multipart.encoder import MultipartEncoder
from datetime import datetime


def uploadPayload(payloadData, log, secrets, fromFile):
    url = secrets["apiURL"]
    apiKey = secrets["apiKey"]
    boundary = "*****"

    log.info(f"Config file apiurl: {secrets}")

    deviceId = payloadData.get('deviceID', "UNKNOWN")
    latitude = str(payloadData.get('latitude', 999))
    longitude = str(payloadData.get('longitude', 999))
    waterColor = str(payloadData.get('waterColor', "n/a"))
    temperature = str(payloadData.get('temperature'))
    dateTime = payloadData.get('device_datetime', datetime.now().isoformat())
    
    # Preparing the data to be sent
    fields = {
        'latitude': latitude,
        'longitude': longitude,
        'deviceID': deviceId,
        'device_datetime': dateTime,
        'waterColor': waterColor,
        'temperature': temperature
    }
    
    currDirectory = os.path.dirname(os.path.abspath(__file__))
    filePath = os.path.join(currDirectory, payloadData["image"])

    log.info(f"Uploading file: {filePath}")
    
    # Adding the image file to the fields
    with open(filePath, 'rb') as file:
        try:
            fields['image'] = (os.path.basename(filePath), file, 'image/jpeg')
            log.info(f"Data being sent: {fields}")

            # Creating a MultipartEncoder
            m = MultipartEncoder(fields=fields, boundary=boundary)
    
            headers = {
                'Content-Type': m.content_type,
                'x-api-key': apiKey
            }
            
            # Sending the request
            response = requests.post(url, data=m, headers=headers)
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

            return True

        except requests.ConnectionError:
            log.error(f"Upload connection error")
            if fromFile == False:
                savePayload(payloadData, log) 
            return False
        except requests.Timeout:
            log.error(f"Upload timeout")
            if fromFile == False:
                savePayload(payloadData, log) 
            return False
        except requests.RequestException as e:
            log.error(f"Upload request exception: {e}")
            if fromFile == False:
                savePayload(payloadData, log) 
            return False
        except Exception as e:
            log.error(f"Upload Exception: {e}")
            if fromFile == False:
                savePayload(payloadData, log) 
            return False
    

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
            # Try to upload the payload
            if uploadPayload(payload, log, secrets, fromFile=True) == True:
                log.info(f"Payload uploaded successfully: {payload['deviceID']}")

                # If upload is successful, remove it from the logs
                logs.remove(payload)

                # Overwrite the file with the remaining failed payloads after each success
                with open(filename, 'w') as f:
                    for remaining_payload in logs:
                        f.write(json.dumps(remaining_payload) + '\n')
            else:
                break

        # Check if all payloads were uploaded
        if not logs:
            log.info("All saved payloads successfully uploaded.")
        else:
            log.error("Some payloads could not be uploaded, saved in the file.")
    else:
        log.info("No saved payloads to upload.")
