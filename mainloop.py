import time
import logging
import gpsSensor
import cameraSensor
import temperatureSensor
import Payload
import platform
import os

interval = 5  # Set interval in seconds
payloadData = {}
logFile = 'waterDeviceLog.txt'
MAX_FILE_SIZE_MB = 50
TRIM_PERCENTAGE = 0.10

# Function to get device ID dynamically from /proc/cpuinfo
def load_device_id():
    try:
        with open('/proc/cpuinfo', 'r') as file:
            for line in file:
                if line.startswith('Serial'):
                    device_id = line.split(':')[1].strip()
                    return device_id
        raise RuntimeError("Serial number not found in /proc/cpuinfo")
    except Exception as e:
        raise RuntimeError("Failed to load device ID") from e

def main():
    # Load the device ID
    device_id = load_device_id()

    # Main loop. Gather all sensor data and upload
    log.info(f"Device ID loaded: {device_id}")
    log.info("Starting main loop...")

    while True:
        try:
            # Capture sensor data
            captureLongLat()
            captureDateTime()
            capturePhoto()
            captureTemperature()
            #captureOxygen()
            #capturepH()
            #captureConductivity()
            #captureTerpidity()

            # Add device ID to payload data
            payloadData['deviceID'] = device_id

            # Upload the payload
            sendDataPayload()
            
        except KeyboardInterrupt:
            log.info("Shutting down...")
            break

        finally:
            log.info(f"*** In main(). Sleeping for {interval} seconds...")
            time.sleep(interval)

def initlog():
    # Create a custom log
    log = logging.getLogger('DWLogger')

    osVersion = platform.version()
    deviceID = load_device_id()  # Dynamically retrieve device ID

    # Clear existing handlers to prevent duplicate logs
    if log.hasHandlers():
        log.handlers.clear()

    # Set the overall logging level
    log.setLevel(logging.DEBUG)

    # Create handlers
    console_handler = logging.StreamHandler()  # Outputs to the CLI
    file_handler = logging.FileHandler('waterDeviceLog.txt')  # Outputs to a file

    # Set logging levels for each handler
    console_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.DEBUG)

    # Create formatters and add them to the handlers
    console_formatter = logging.Formatter(f'%(asctime)s - {deviceID} - {osVersion} - %(name)s - %(levelname)s - %(message)s')
    file_formatter = logging.Formatter(f'%(asctime)s - {deviceID} - {osVersion} - %(name)s - %(levelname)s - %(message)s')

    console_handler.setFormatter(console_formatter)
    file_handler.setFormatter(file_formatter)

    # Add the handlers to the logger
    log.addHandler(console_handler)
    log.addHandler(file_handler)

    return log


def trim_log_file():
    with open(logFile, 'r') as file:
        lines = file.readlines()

    # Calculate the number of lines to remove
    num_lines = len(lines)
    lines_to_remove = int(num_lines * TRIM_PERCENTAGE)

    if lines_to_remove > 0:
        # Remove the oldest lines
        remaining_lines = lines[lines_to_remove:]

        # Write the remaining lines back to the file
        with open(logFile, 'w') as file:
            file.writelines(remaining_lines)

def manage_log_file():
    # Check file size
    file_size_mb = os.path.getsize(logFile) / (1024 * 1024)  # Convert to MB

    if file_size_mb > MAX_FILE_SIZE_MB:
        log.info(f"Log file exceeds {MAX_FILE_SIZE_MB} MB. Trimming the file.")
        trim_log_file()

def capturePhoto():
    imagePath = cameraSensor.captureCameraImage(log)
    if imagePath:
        payloadData.update({"image": imagePath})

def captureTemperature():
    return temperatureSensor.captureTemperature(log)

def captureLongLat():
    loc = gpsSensor.getLoc(log)
    if loc:
        payloadData.update(loc)

def captureDateTime():
    dateTime = gpsSensor.getGPSTime(log)
    if dateTime:
        payloadData.update({"dateTime": dateTime})

def sendDataPayload():
    Payload.uploadPayload(payloadData, log)

if __name__ == "__main__":
    log = initlog()
    main()
