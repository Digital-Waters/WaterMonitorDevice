import requests
import os
import json
from requests_toolbelt.multipart.encoder import MultipartEncoder
from datetime import datetime, timezone


# The device's payloadData still uses the historical snake_case keys, but the v2
# API (POST /api/v1/captures) expects camelCase and identifies a device by its
# hardware serial in `deviceCode`. All of that translation happens here so that
# mainloop.py and the sensor modules stay untouched.
#
# Only these optional measurements have a matching v2 column; anything else the
# device sends (e.g. latitude/longitude) is forwarded verbatim and preserved by
# v2 in rawPayload rather than dropped.
_OPTIONAL_FIELD_MAP = {
    'water_temperature':   'waterTemperature',
    'sensor_ph':           'pH',
    'sensor_orp':          'orp',
    'sensor_conductivity': 'conductivity',
}

# v2 has no capture-level latitude/longitude column (coordinates belong to the
# deployment/location). We still forward them when present so a reading is never
# silently lost — v2 keeps unmapped fields in rawPayload.
_PASSTHROUGH_FIELDS = ('latitude', 'longitude')


def _isSuccess(statusCode):
    """A capture is safely stored on either status.

    201 -> a new capture was created.
    200 -> an identical (device, captureDateTime) was already stored; the device
           is resending from its backlog and v2 answered idempotently. Either way
           the server has the data, so treat both as success and stop retrying.
    """
    return statusCode in (200, 201)


def _buildCaptureBody(payloadData, log):
    """Translate the device's snake_case payloadData into the v2 upload schema."""
    body = {
        # Required by v2. deviceCode is the hardware serial (the device's
        # /proc/cpuinfo Serial), which must be provisioned in v2 or the upload
        # 404s. captureDateTime is required and must be present.
        'deviceCode': payloadData.get('deviceID', 'UNKNOWN'),
        'captureDateTime': payloadData.get(
            'capture_datetime', datetime.now(timezone.utc).isoformat()
        ),
    }

    for src, dst in _OPTIONAL_FIELD_MAP.items():
        value = payloadData.get(src)
        if value is not None:
            body[dst] = value
        else:
            log.info(f"Field '{src}' is null or not present, excluding from capture.")

    # waterRgba is a String column in v2. getRgbaFromImage() returns a dict; its
    # Python repr ({'r': .., 'g': .., 'b': .., 'a': ..}, single-quoted) is the
    # exact format legacy consumers (e.g. the public dashboard) already parse, so
    # match it rather than emitting JSON.
    rgba = payloadData.get('water_rgba')
    if rgba is not None:
        body['waterRgba'] = str(rgba)

    for field in _PASSTHROUGH_FIELDS:
        value = payloadData.get(field)
        if value is not None:
            body[field] = value

    return body


def _resolveImagePath(payloadData, log):
    """Absolute path of the image to upload, or None to upload imageless.

    A saved/backlogged payload may reference an image that has since been deleted
    from disk (e.g. by image cleanup). Degrading to an imageless upload keeps the
    measurement landing and clears the poison entry from the backlog instead of
    blocking the drain forever.
    """
    image = payloadData.get("image")
    if image is None:
        log.warning("No image available, uploading capture without image.")
        return None

    currDirectory = os.path.dirname(os.path.abspath(__file__))
    filePath = os.path.join(currDirectory, image)
    if not os.path.exists(filePath):
        log.warning(
            f"Image file no longer exists, uploading capture without image: {filePath}"
        )
        return None
    return filePath


def _retryLoop(doPost, log, maxRetries):
    """Run doPost() up to maxRetries times, retrying only on network errors.

    A 4xx/5xx is a definitive answer (validation, auth, unknown device, oversized
    image) that a retry will not change, so we log the detail and stop. Only a
    transient connection/timeout is worth another attempt.
    """
    for attempt in range(1, maxRetries + 1):
        try:
            log.info(f"Upload attempt {attempt} of {maxRetries}")
            response = doPost()

            if _isSuccess(response.status_code):
                log.info(f"Successfully uploaded capture to API ({response.status_code})")
                return True

            log.error(f"Upload failed: {response.status_code} - {response.reason}")
            log.error(f"Response Text: {response.text}")
            log.error(f"Response Headers: {response.headers}")
            return False

        except (requests.ConnectionError, requests.Timeout) as e:
            log.warning(f"Network error on attempt {attempt}: {e}")

        except requests.RequestException as e:
            log.error(f"Request exception: {e}")
            return False

        except Exception as e:
            log.error(f"Unexpected exception during upload: {e}")
            return False

    return False


def _postCapture(url, apiKey, body, imagePath, log, maxRetries, timeoutSeconds):
    """POST one capture to v2, with or without an image.

    Imageless -> a plain JSON body. With an image -> multipart/form-data carrying
    a `metadata` part (the JSON body) plus an `image` file part, which is the
    shape v2's POST /api/v1/captures expects.
    """
    if imagePath is None:
        def doPost():
            headers = {'Content-Type': 'application/json', 'x-api-key': apiKey}
            return requests.post(
                url, data=json.dumps(body), headers=headers, timeout=timeoutSeconds
            )
        return _retryLoop(doPost, log, maxRetries)

    log.info(f"Uploading capture with image: {imagePath}")
    try:
        with open(imagePath, 'rb') as f:
            def doPost():
                # Rewind so each retry re-reads the file from the start.
                f.seek(0)
                # `metadata` is sent as a plain string field (no filename), so v2
                # parses it as the JSON body rather than treating it as a file.
                fields = {
                    'metadata': json.dumps(body),
                    'image': (os.path.basename(imagePath), f, 'image/jpeg'),
                }
                m = MultipartEncoder(fields=fields)
                headers = {'Content-Type': m.content_type, 'x-api-key': apiKey}
                return requests.post(
                    url, data=m, headers=headers, timeout=timeoutSeconds
                )
            return _retryLoop(doPost, log, maxRetries)
    except OSError as fileError:
        # The image vanished between the existence check and open(), or is
        # otherwise unreadable. Fall back to an imageless upload so one bad image
        # does not permanently block this measurement and the backlog behind it.
        log.error(f"Error opening image file, uploading without image: {fileError}")
        return _postCapture(url, apiKey, body, None, log, maxRetries, timeoutSeconds)


def uploadPayload(payloadData, log, secrets, fromFile, maxRetries=3):
    url = secrets["apiURL"]
    apiKey = secrets["apiKey"]
    timeoutSeconds = 15  # network timeout so we don't hang

    body = _buildCaptureBody(payloadData, log)
    imagePath = _resolveImagePath(payloadData, log)

    uploaded = _postCapture(url, apiKey, body, imagePath, log, maxRetries, timeoutSeconds)

    if uploaded:
        # Only a live capture drains the backlog; a backlog replay (fromFile)
        # must not recurse into another drain.
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
