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

    # Required fields — always sent
    fieldsBase = {
        'deviceID': payloadData.get('deviceID', 'UNKNOWN'),
        'capture_datetime': payloadData.get('capture_datetime', datetime.now().isoformat()),
    }

    # Optional fields — only sent if present and non-null
    optional_fields = [
        'latitude',
        'longitude',
        'water_rgba',
        'water_temperature',
        'sensor_ph',
        'sensor_orp',
        'sensor_conductivity',
    ]

    for field in optional_fields:
        value = payloadData.get(field)
        if value is not None:
            fieldsBase[field] = str(value)
        else:
            log.info(f"Field '{field}' is null or not present, excluding from payload.")

    image = payloadData.get("image")

    # A saved/backlogged payload may reference an image that has since been
    # deleted from disk (e.g. by image cleanup). Trying to open it raises
    # [Errno 2] and, treated as a failure, permanently blocks the backlog
    # drain. Degrade to an imageless upload so the measurement still lands and
    # the poison entry clears from the backlog.
    if image is not None:
        currDirectory = os.path.dirname(os.path.abspath(__file__))
        filePath = os.path.join(currDirectory, image)
        if not os.path.exists(filePath):
            log.warning(
                f"Image file no longer exists, uploading payload without image: {filePath}"
            )
            image = None

    if image is None:
        log.warning("No image available, uploading payload without image.")
        uploaded = False
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
                    uploaded = True
                    break
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
                log.error(f"Unexpected exception during upload: {e}")
                break

        if uploaded:
            if not fromFile:
                try:
                    uploadSavedPayloads(log, secrets)
                except Exception as e:
                    log.error(f"Error draining saved payloads: {e}")
            return True

        if not fromFile:
            savePayload(payloadData, log)
        return False

    currDirectory = os.path.dirname(os.path.abspath(__file__))
    filePath = os.path.join(currDirectory, image)
    log.info(f"Uploading file: {filePath}")

    uploaded = False
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
                        uploaded = True
                        break
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
                    log.error(f"Unexpected exception during upload: {e}")
                    break

    except Exception as fileError:
        log.error(f"Error opening image file: {fileError}")

    if uploaded:
        if not fromFile:
            try:
                uploadSavedPayloads(log, secrets)
            except Exception as e:
                log.error(f"Error draining saved payloads: {e}")
        return True

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
            logs = [json.loads(line.strip()) for line in f.readlines() if line.strip()]

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
