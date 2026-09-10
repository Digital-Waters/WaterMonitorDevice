import time
from datetime import datetime, timezone
import logging
from logging.handlers import RotatingFileHandler
import cameraSensor
import temperatureSensor
import conductivitySensor
import phSensor
import orpSensor
import payload
import platform
from configparser import ConfigParser
import configWriter
import imageToRGBA


interval = 5  # Set interval in seconds
# Rolling-log defaults (overridable in waterMonitor.ini [GENERAL]):
# each log file grows to LogMaxFileSizeMB, then rolls over; we keep LogFileCount
# files total (the active file plus rolled backups), so at most
# LogMaxFileSizeMB * LogFileCount MB on disk.
LogMaxFileSizeMB = 5
LogFileCount = 20
payloadData = {}
logFile = 'waterDeviceLog.txt'
apikey = ""

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
    global interval, sensors, secrets
    config = ConfigParser(interpolation=None)

    try:
        config.read("waterMonitor.ini")
        interval = int(config["GENERAL"]["sleepInterval"])
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
            capturePhoto(deviceID)
            captureTemperature()
            captureConductivity()
            capturepH()
            captureORP()
            #captureTerpidity()
            
            # Add device ID to payload data
            payloadData['deviceID'] = deviceID
            # UTC with an explicit offset: v2 interprets a naive timestamp as
            # UTC, so sending local Pi time (no offset) would store the wrong
            # instant if the device's clock is not on UTC.
            payloadData['capture_datetime'] = datetime.now(timezone.utc).isoformat()
            
            log.info(f"Config file apiurl: {secrets}")
    
            # Upload the payload
            sendDataPayload()

        except KeyboardInterrupt:
            log.info("Shutting down...")
            break

        #finally:
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

    # Read rolling-log settings from the config with safe fallbacks. initlog()
    # runs before getConfig(), so we read the ini directly here; if it is missing
    # (fresh device) the fallbacks apply.
    logConfig = ConfigParser(interpolation=None)
    logConfig.read("waterMonitor.ini")
    maxFileSizeMB = logConfig.getint("GENERAL", "LogMaxFileSizeMB", fallback=LogMaxFileSizeMB)
    fileCount = logConfig.getint("GENERAL", "LogFileCount", fallback=LogFileCount)

    # Create handlers
    console_handler = logging.StreamHandler()  # Outputs to the CLI
    # Rolling file handler: once the active log passes maxFileSizeMB it is rolled
    # to waterDeviceLog.txt.1, existing backups shift up (.1 -> .2 -> ...), and
    # the oldest beyond backupCount is deleted. Keeping (fileCount - 1) backups
    # plus the active file gives fileCount files, capped at fileCount * maxFileSizeMB.
    file_handler = RotatingFileHandler(
        logFile,
        maxBytes=maxFileSizeMB * 1024 * 1024,
        backupCount=max(fileCount - 1, 0),
    )  # Outputs to a rolling set of files

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

def capturePhoto(deviceID):
    imagePath = cameraSensor.captureCameraImage(log, deviceID)
    if imagePath:
        payloadData.update({"image": imagePath})
        rgba = imageToRGBA.getRgbaFromImage(imagePath)
        log.info(f"RGBA: {rgba}")
        payloadData.update({"water_rgba": rgba})
    else:
        payloadData.update({"image": None})

def captureTemperature():
    payloadData.update({"water_temperature": temperatureSensor.captureTemperature(log)})

def captureConductivity():
    payloadData.update({"sensor_conductivity": conductivitySensor.captureConductivity(log)})

def capturepH():
    payloadData.update({"sensor_ph": phSensor.capturepH(log)})

def captureORP():
    payloadData.update({"sensor_orp": orpSensor.captureORP(log)})

def sendDataPayload():
    payload.uploadPayload(payloadData, log, secrets, fromFile=False)

if __name__ == "__main__":
    log = initlog()
    getConfig()
    main()
