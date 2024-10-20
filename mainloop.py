import time
import logging
#import gpsSensor
import cameraSensor
import temperatureSensor
import Payload
import platform
import os
from configparser import ConfigParser
import configWriter
import imageToRGBA


interval = 5  # Set interval in seconds
MaxFileSize = 50
TrimPercent = 0.10
timeZone = "America/Toronto"
payloadData = {}
logFile = 'waterDeviceLog.txt'
referenceImage = "referenceImage.jpg"

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

def getConfig(): 
    global interval, MaxFileSize, TrimPercent, sensors, secrets, timeZone
    config = ConfigParser()

    try:
        config.read("waterMonitor.ini")
        interval = int(config["GENERAL"]["sleepInterval"])
        MaxFileSize = int(config["GENERAL"]["MaxFileSize"])
        TrimPercent = float(config["GENERAL"]["TrimPercent"])
        secrets = config["SECRETS"]
        log.info("successfully parsed the config file!")
    except:
        configWriter.createConfig()
        getConfig()
        log.error("error parsing config file, will use default values!")


def main():
    # Load the device ID
    deviceID = load_device_id()

    # Main loop. Gather all sensor data and upload
    log.info(f"Device ID loaded: {deviceID}")
    log.info("Starting main loop...")

    while True:
        try:
            # Capture sensor data
            #captureLongLat()
            #captureGPSDateTime()
            capturePhoto(deviceID)
            captureTemperature()
            #captureConductivity()
            #captureTerpidity()
            
            # Add device ID to payload data
            payloadData['deviceID'] = deviceID

            # Upload the payload
            sendDataPayload()

            manageLogFile()
            
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

def trimLogFile():
    with open(logFile, 'r') as file:
        lines = file.readlines()

    # Calculate the number of lines to remove
    numLines = len(lines)
    linesToRemove = int(numLines * TrimPercent)

    if linesToRemove > 0:
        # Remove the oldest lines
        remainingLines = lines[linesToRemove:]

        # Write the remaining lines back to the file
        with open(logFile, 'w') as file:
            file.writelines(remainingLines)

def manageLogFile():
    # Check file size
    fileSize = os.path.getsize(logFile) / (1024 * 1024)  # Convert to MB

    if fileSize > MaxFileSize:
        log.info(f"Log file exceeds {MaxFileSize} MB. Trimming the file.")
        trimLogFile()
    else: 
        log.info(f"Log file size is under {MaxFileSize} MB")

def capturePhoto(deviceID):
    imagePath = cameraSensor.captureCameraImage(log, deviceID)
    if imagePath:
        payloadData.update({"image": imagePath})
        rgba = imageToRGBA.getRgbaFromImage(imagePath, referenceImage)
        log.info(f"RGBA: {rgba}")
        payloadData.update({"waterColor": rgba})

def captureTemperature():
    payloadData.update({"temperature": temperatureSensor.captureTemperature(log)})

def captureLongLat():
    loc = gpsSensor.getLoc(log)
    if loc:
        payloadData.update(loc)

def captureGPSDateTime():
    dateTime = gpsSensor.getGPSTime(log, timeZone)
    if dateTime:
        payloadData.update({"dateTime": dateTime})

def sendDataPayload():
    Payload.uploadPayload(payloadData, log, secrets, fromFile=False)

if __name__ == "__main__":
    log = initlog()
    getConfig()
    main()
