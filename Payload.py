import requests
import os
import json
import subprocess
from requests_toolbelt.multipart.encoder import MultipartEncoder
from datetime import datetime

# --- Wi-Fi helpers (Bookworm + NetworkManager) ---
WIFI_IFACE = "wlan0"

def runCmd(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def wifiOff(log=None):
    # Hard shut RF; don’t call nmcli
    runCmd("rfkill block wifi")
    # Optionally also bring link down (harmless if rfkill blocks it)
    runCmd(f"ip link set {WIFI_IFACE} down")
    if log: log.info("Wi-Fi powered down (rfkill).")

def isWifiAssociated(log=None):
    out = runCmd(f"iw dev {WIFI_IFACE} link").stdout.strip()
    if not out or "Not connected" in out:
        if log: log.debug("iw link: not connected")
        return False
    ssid = ""
    for line in out.splitlines():
        if line.strip().startswith("SSID:"):
            ssid = line.split("SSID:", 1)[1].strip()
            break
    if log: log.debug(f"iw link: associated to SSID='{ssid or 'unknown'}'")
    return True

def isNetworkUsable(apiUrl, log=None):
    # Only check L3 basics; no NetworkManager calls
    ipLine = runCmd(f"ip -o -4 addr show dev {WIFI_IFACE}").stdout.strip()
    routeLine = runCmd(f"ip route show default dev {WIFI_IFACE}").stdout.strip()
    if not ipLine or not routeLine:
        if log: log.debug(f"isNetworkUsable: hasIp={bool(ipLine)}, hasDefaultRoute={bool(routeLine)}")
        return False
    u = urlparse(apiUrl); host, port = u.hostname, (u.port or (443 if u.scheme=='https' else 80))
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


def uploadPayload(payloadData, log, secrets, fromFile, maxRetries=3):
    import time

    url = secrets["apiURL"]
    apiKey = secrets["apiKey"]
    boundary = "*****"
    timeoutSeconds = 15  # network timeout so we don't hang

    deviceId = payloadData.get('deviceID', "UNKNOWN")
    latitude = str(payloadData.get('latitude', '999'))
    longitude = str(payloadData.get('longitude', '999'))
    waterColor = str(payloadData.get('waterColor', '999'))
    temperature = str(payloadData.get('temperature', '999'))
    dateTime = payloadData.get('device_datetime', datetime.now().isoformat())

    fieldsBase = {
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

    # If we already know we're not connected, save power immediately.
    if not isWifiAssociated(log):
        log.warning("No network connection detected before upload. Powering Wi-Fi down.")
        wifiOff(log)
        if not fromFile:
            savePayload(payloadData, log)
        return False

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
                        # Server responded (likely reachable). No need to power down Wi-Fi here.
                        break  # avoid retry storms on 4xx/5xx unless you specifically want to

                except (requests.ConnectionError, requests.Timeout) as e:
                    log.warning(f"Network error on attempt {attempt}: {e}")
                    # If we lost association entirely, shut Wi-Fi off; otherwise keep it up for local app.
                    if not isWifiAssociated(log):
                        log.warning("Lost Wi-Fi association. Powering Wi-Fi down.")
                        wifiOff(log)
                        break

                except requests.RequestException as e:
                    # Other request-layer issues. Don't power Wi-Fi off automatically.
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
