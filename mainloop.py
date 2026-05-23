import time
from datetime import datetime
import logging
#import gpsSensor
import cameraSensor
import temperatureSensor
import payload
import platform
import os
from configparser import ConfigParser
import configWriter
import imageToRGBA
import subprocess
from typing import Union
import binascii


# I think what we want is a dictionary with all the sensors in it so we can just call
# the following commands using that data structure

AS_SENSOR_INFO = [
    {'addr':0x61, 'name':'sensor_do'},
    {'addr':0x62, 'name':'sensor_orp'},
    {'addr':0x63, 'name':'sensor_ph'},
    {'addr':0x64, 'name':'sensor_conductivity'},
    {'addr':0x66, 'name':'temperature'}
]

class EzoSensor:
    """
    Atlas Scientific EZO sensors can use this class to manage their instances.
    """
      
    def i2c_send_cmd_get_resp(self, cmd:str) -> Union[bool, str]:
        """
        Uses subprocess.run to call i2ctransfer with the specified Atlas Scientific command. 
        Note that cmd must be hexified first.
        If the command fails or there is no device at the specified address False is returned.
        Otherwise the data-only portion of the response string is returned.    
        """
        
        try:
            ret = subprocess.run(f'i2ctransfer -y 1 w1@{self.addr} {cmd}',
                                 shell=True, capture_output=True)
            
            if ret.returncode != 0:
                return False
    
            time.sleep(1.0)
    
            ret = subprocess.run(f'i2ctransfer -y 1 r40@{self.addr}',
                                 shell=True, capture_output=True, encoding="utf-8")
    
            if ret.returncode != 0:
                return False
    
            # Check that the first hex character is a 1 otherwise the command failed
            if ret.stdout[:4] != '0x01':
                # log.info(ret.stdout[0])
                return False
    
            # log.info(ret.stdout)
            # remove extraneous characters to prep for unhexlify-ing starting after the status char
            s = ret.stdout[4:]
            s = s.replace('0x00', '')
            s = s.replace('0x', '')
            s = s.replace(' ', '')
            s = s.replace('\n', '') 
            
            return binascii.unhexlify(s)
                
                
        except Exception as e:
            log.error(e.with_traceback());
            return False
        
    
    def ping(self) -> bool:
        """
        Attempts to contact the ezo board using the info command. Returns True and sets
        the self.present flag if the ezo board responded 
        """
        if self.get_info() != False:
            self.present = True;
        else:
            # This isn't strictly necessary but we may want to use this as some kind of 
            # heartbeat if we find sensors dropping off the bus
            self.present = False;
            
        return self.present
        
    
    def get_info(self) -> Union[bool, str]:
        """
        Attempts to read the info string from the EZO board
        """        
        info = self.i2c_send_cmd_get_resp(hex(ord('i')))
        
        if info != False:
            # info is returned raw, for the data string we need to skip the first 3 characters 
            self.info = info[3:]
            # log.info(self.info)
             
        return info
            
            
    def get_reading( self, timeout:float=1.0 ) -> bool:
        """
        Attempts to trigger a sensor reading and stores the value read into 
        self.last_reading. 
        Returns True if a value was read or False otherwise
        """
        if self.present:
            ret = self.i2c_send_cmd_get_resp(hex(ord('R')))
            if ret != False:
                self.last_reading = ret  
                return True 
        return False
        
    def __init__(self, sensor_addr:int, sensor_name:str):
        self.present: bool = False
        self.addr:int = sensor_addr
        self.name:str = sensor_name
        self.info:str = ''
        self.last_reading:str = ''

# Instantiate all the ezo sensors listed in AS_SENSOR_INFO list      
as_sensors=[EzoSensor(i['addr'], i['name']) for i in AS_SENSOR_INFO]

interval = 5  # Set interval in seconds
MaxFileSize = 50
TrimPercent = 0.10
timeZone = "America/Toronto"
payloadData = {}
logFile = 'waterDeviceLog.txt'
referenceImage = "referenceImage.jpg"
apikey = ""
log = None

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
    config = ConfigParser(interpolation=None)

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

    # check each AS sensor to see if it is installed and responding
    for sensor in as_sensors:
        if sensor.ping():
            log.info(f'Atlas Scientific {sensor.name} detected')

    while True:
        try:
            # Capture sensor data
            #captureLongLat()
            #captureGPSDateTime()
            capturePhoto(deviceID)
            captureTemperature()
            #captureConductivity()
            #captureTerpidity()
            for sensor in as_sensors:
                if sensor.get_reading():   
                    payloadData.update({sensor.name: sensor.last_reading}) 
                    log.info(f'{sensor.name}: {sensor.last_reading}')

            
            # Add device ID to payload data
            payloadData['deviceID'] = deviceID
            payloadData['capture_datetime'] = datetime.now().isoformat()
            
            log.info(f"Config file apiurl: {secrets}")
    
            # Upload the payload
            sendDataPayload()

            manageLogFile()
            
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
    if cameraSensor.cameraPresent:
        imagePath = cameraSensor.captureCameraImage(log, deviceID)
        if imagePath:
            payloadData.update({"image": imagePath})
            rgba = imageToRGBA.getRgbaFromImage(imagePath, referenceImage)
            log.info(f"RGBA: {rgba}")
            payloadData.update({"water_rgba": rgba})
        else:
            payloadData.update({"image": None})
            payloadData.update({"water_rgba": None})
            

def captureTemperature():
    payloadData.update({"water_temperature": temperatureSensor.captureTemperature(log)})

def captureLongLat():
    loc = gpsSensor.getLoc(log)
    if loc:
        payloadData.update(loc)

def captureGPSDateTime():
    dateTime = gpsSensor.getGPSTime(log, timeZone)
    if dateTime:
        payloadData.update({"dateTime": dateTime})

def sendDataPayload():
    payload.uploadPayload(payloadData, log, secrets, fromFile=False)

if __name__ == "__main__":
    log = initlog()
    getConfig()
    main()
