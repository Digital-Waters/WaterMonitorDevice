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

    while True:
        try:
            # Capture sensor data
            #captureLongLat()
            #captureGPSDateTime()
            capturePhoto(deviceID)
            captureTemperature()
            captureTemperatureEZO()
            #captureConductivity()
            #captureTerpidity()
            
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

# Note that all AS EZO boards support the "i" command so we can do this as a table
# to make things a bit easier 

def i2c_get_info( addr:int=0 ) -> Union[bool, str]:
    """
    Uses subprocess.run to call i2ctransfer with the Atlas Scientific 'i' command to the 
    I2C address specified by addr.
    If the command fails or there is no device at the specified address False is returned.
    Otherwise the data-only portion of the info string is returned.    
    """
    try:
       
        # write the info command 'i' (0x69)
        ret = subprocess.run(f'i2ctransfer -y 1 w1@{addr} 0x69',
                             shell=True, capture_output=True)
        
        if ret.returncode != 0:
            return False

        ret = subprocess.run(f'i2ctransfer -y 1 r40@{addr}',
                             shell=True, capture_output=True, encoding="utf-8")

        log.info(ret)
        
        if ret.returncode != 0:
            return False

        log.info(ret.stdout[:4])

        # Check that the first hex character is a 1 otherwise the command failed
        if ret.stdout[:4] != '0x01':
            log.info(ret.stdout[0])
            return False

        # TODO: trim the first 4 hex digits off, it's the return value a comma and
        # i for the i command:
        # 1?i,<actual response string>
        # A hex digit in this case is 0xXX_ where _ is a whitespace
        s = ret.stdout[5*4:]
                        
        s = s.replace('0x00', '')
        s = s.replace('0x', '')
        s = s.replace(' ', '')
        s = s.replace('\n', '') 
        log.info(s)
        
        info = binascii.unhexlify(s)
        log.info(info)

        return info
            
            
    except Exception as e:
        log.error(e.with_traceback());
        return False
        
        
def i2c_get_reading( addr:int=0, timeout:float=1.0 ) -> Union[bool, str]:
    """
    Uses subprocess.run to call i2ctransfer with the Atlas Scientific 'R' command to the 
    I2C address specified by addr.
    If the command fails or there is no device at the specified address False is returned.
    Otherwise the data-only portion of the reading string is returned.    
    """
    try:
       
        # write the info command 'R' (0x52)
        ret = subprocess.run(f'i2ctransfer -y 1 w1@{addr} 0x52',
                             shell=True, capture_output=True)

        log.info(ret)

        if ret.returncode != 0:
            return False

        ret = subprocess.run(f'i2ctransfer -y 1 r40@{addr}',
                             shell=True, capture_output=True)

        if ret.returncode != 0:
            return False
        
        log.info(ret)

        # Check that the first hex character is a 1 otherwise the command failed
        if ret.stdout[:4] != '0x01':
            return False

        # TODO: trim the first 4 hex digits off, it's the return value a comma and
        # i for the i command:
        # 1?i,<actual response string>
        # A hex digit in this case is 0xXX_ where _ is a whitespace
        s = ret.stdout[5*4:]
                        
        s = s.replace('0x00', '')
        s = s.replace('0x','')
        s = s.replace(' ','')
        log.info(s)
        return binascii.unhexlify(s)
            
            
    except Exception as e:
        log.error(e.with_traceback());
        return False
            


# Move this to it's own driver file
def captureTemperatureEZO():
    """
    If an Atlas Scientific EZO temperature sensor is present call this to 
    get the temperature readings from the I2C bus
    """
    ezo_temp_addr = 0x66

    # Note(AZT 20260521): I feel like we should probably probe all the sensors
    # in some initialization code, then all we have to do is read the values

    try:
        
        ret = i2c_get_info(ezo_temp_addr)
        
        if(ret == False):
            log.error("AS EZO-RTD not present")
            return None

        log.info(f"AS RTD EZO detected: {ret}")
        
        
        # else we have our info string from the device 
        
        # # write the info command 'i'
        # ret = subprocess.run(f'i2ctransfer -y 1 w1@{ezo_temp_addr} 0x69', 
        #                      shell=True, capture_output=True)
        #
        #
        # if ret.returncode == 0:
        #
        #     ret = subprocess.run(f'i2ctransfer -y 1 r20@{ezo_temp_addr}');
    
        # TODO: trim the first 4 hex digits off, it's the return value a comma and
        # i for the i command:
        # 1?i,<actual response string>
                                
        # s=ret.stdout[4:].replace('0x','')
        # s=s.replace(' ','')
        # binascii.unhexlify(s)
        
        # parse the info string, make sure it's an RTD
        
        # Now we know that we have a temp sensor, run the 'i' command
        # to get a reading
        
        # wait 600ms
        
        # read the result
        
        # else:
        # # Error running the first comand -- Maybe no temp sensor 
        # pass
        
        
        
        # # if ret contains an "Error" string then we failed
        # if ret == 0:
        #     # There's something at that address, read back the data
        #     ret = os.system(f'i2ctransfer -y 1 r10@{ezo_temp_addr}')
        #
        #     if 
        #
        #     pass
        # else:
        #     # We failed, TODO: check the return value
        #     pass
        
        # Check for the temperature sensor
    #     device_folder = glob.glob(base_dir + '28*')[0]
    #     device_file = device_folder + '/w1_slave'
    #
    #     lines = read_temp_raw(device_file)
    #     while lines[0].strip()[-3:] != 'YES':
    #         time.sleep(0.2)
    #         lines = read_temp_raw(device_file)
    #     equals_pos = lines[1].find('t=')
    #     if equals_pos != -1:
    #         temp_string = lines[1][equals_pos+2:]
    #         temp_c = float(temp_string) / 1000.0
    #
    #         log.info(f"Temperature: {temp_c} Celcius")
    #         return temp_c
    #
    # except IndexError:
    #     log.info("No temperature sensor connected.")
    #     return None
    except Exception as e:
        log.error(e.with_traceback())
        
        return None
    # payloadData.update({"water_temperature": temperatureSensor.captureTemperature(log)})


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
