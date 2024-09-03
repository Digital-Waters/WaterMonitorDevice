import time
import logging
import gpsSensor
import cameraSensor
import temperatureSensor
import platform
import os

# Constants
interval = 5  # Set interval in seconds
payloadData = {}
logFile = 'waterDeviceLog.txt'
MAX_FILE_SIZE_MB = 50
TRIM_PERCENTAGE = 0.10

# Load device ID function
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
    # Main loop
    log.info("Starting main loop...")

    while True:
        try:
            captureLongLat()
            capturePhoto()
            #captureTemperature()
            #captureOxygen()
            #capturepH()
            #captureConductivity()
            #captureTerpidity()

            #sendDataPayload()
            
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
    
    # Load the actual device ID using the load_device_id function
    try:
        deviceID = load_device_id()
    except RuntimeError as e:
        deviceID = "UNKNOWN"
        print(f"Error loading device ID: {e}")

    # Clear existing handlers to prevent duplicate logs
    if log.hasHandlers():
        log.handlers.clear()

    # Set the overall logging level
    log.setLevel(logging.DEBUG)

    # Create handlers
    console_handler = logging.StreamHandler()  # Outputs to the CLI
    file_handler = logging.FileHandler(logFile)  # Outputs to a file

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
    temperatureSensor.captureTemperature()

def captureLongLat():
    loc = gpsSensor.getLoc(log)

    if loc:
        payloadData.update(loc)

if __name__ == "__main__":
    log = initlog()
    main()
