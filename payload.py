import requests
import os
import json
from requests_toolbelt.multipart.encoder import MultipartEncoder
from datetime import datetime


def uploadPayload(payloadData, log, secrets, fromFile, maxRetries=3):
    import time

    url = secrets["apiURL"]
    apiKey = secrets["apiKey"]
    boundary = "*****"
    timeoutSeconds = 15  # network timeout so we don't hang

    deviceId = payloadData.get('deviceID', "UNKNOWN")
    latitude = str(payloadData.get('latitude', '999'))
    longitude = str(payloadData.get('longitude', '999'))
    waterColor = str(payloadData.get('water_rgba', '999'))
    dateTime = payloadData.get('capture_datetime', datetime.now().isoformat())

    fieldsBase = {
        'latitude': latitude,
        'longitude': longitude,
        'deviceID': deviceId,
        'capture_datetime': dateTime,
        'water_rgba': waterColor,
    }

    temperature = payloadData.get('water_temperature')
    if temperature is not None:
        fieldsBase['water_temperature'] = str(temperature)

    phSensor = payloadData.get('sensor_ph')
    if phSensor is not None:
        fieldsBase['sensor_ph'] = str(phSensor)
        
    orpSensor = payloadData.get('sensor_orp')
    if orpSensor is not None:
        fieldsBase['sensor_orp'] = str(orpSensor)

    conductivitySensor = payloadData.get('sensor_conductivity')
    if conductivitySensor is not None:
        fieldsBase['sensor_conductivity'] = str(conductivitySensor)

    image = payloadData.get("image")

    if image is None:
        log.warning("No image available, uploading payload without image.")
        for attempt in range(1, maxRetries + 1):
            try:
                log.info(f"Attempt {attempt} of {maxRetries} (no image)")
                m = MultipartEncoder(fields=fieldsBase, boundary=boundary)
                headers = {
                    'Content-Type': m.content_type,
                    'x-api-key': apiKey
                }
                response = requests.post(url, data=m, headers=headers, timeout=timeoutSeconds)
                if response.status_code == 200:
                    log.info("Successfully uploaded payload to DB")
                    if not fromFile:
                        uploadSavedPayloads(log, secrets)
                    return True
                else:
                    log.error(f"Upload failed: {response.status_code} - {response.reason}")
                    log.error(f"Response Text: {response.text}")
                    log.error(f"Response Headers: {response.headers}")
                    break
            except (requests.ConnectionError, requests.Timeout) as e:
                log.warning(f"Network error on attempt {attempt}: {e}")
            except requests.RequestException as e:
                log.error(f"Request exception: {e}")
                break
            except Exception as e:
                log.error(f"Unexpected exception: {e}")
                break
        if not fromFile:
            savePayload(payloadData, log)
        return False

    currDirectory = os.path.dirname(os.path.abspath(__file__))
    filePath = os.path.join(currDirectory, image)
    log.info(f"Uploading file: {filePath}")

    try:
        with open(filePath, 'rb') as f:
            for attempt in range(1, maxRetries + 1):
                try:
                    log.info(f"Attempt {attempt} of {maxRetries}")

                    # Rebuild fields + encoder (and rewind the file) each attempt
                    f.seek(0)
                    fields = dict(fieldsBase)
                    fields['image'] = (os.path.basename(filePath), f, 'image/jpeg')
                    m = MultipartEncoder(fields=fields, boundary=boundary)
                    headers = {
                        'Content-Type': m.content_type,
                        'x-api-key': apiKey
                    }

                    response = requests.post(url, data=m, headers=headers, timeout=timeoutSeconds)

                    if response.status_code == 200:
                        log.info("Successfully uploaded payload to DB")
                        if not fromFile:
                            uploadSavedPayloads(log, secrets)
                        return True
                    else:
                        log.error(f"Upload failed: {response.status_code} - {response.reason}")
                        log.error(f"Response Text: {response.text}")
                        log.error(f"Response Headers: {response.headers}")
                        break  # avoid retry storms on 4xx/5xx

                except (requests.ConnectionError, requests.Timeout) as e:
                    log.warning(f"Network error on attempt {attempt}: {e}")

                except requests.RequestException as e:
                    log.error(f"Request exception: {e}")
                    break

                except Exception as e:
                    log.error(f"Unexpected exception: {e}")
                    break

    except Exception as fileError:
        log.error(f"Error opening image file: {fileError}")

    if not fromFile:
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
