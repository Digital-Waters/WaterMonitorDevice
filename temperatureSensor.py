import os
import logging

sysDevicesPath = '/sys/bus/w1/devices/'
notDeviceName = 'w1_bus_master1'
temperatureDeviceName = '/w1_slave'
log = logging.getLogger('DWLogger')


def captureTemperature():
    
    log.info(f"In captureTemperature()")

    try:
        for i in os.listdir(sysDevicesPath):
            if i != notDeviceName:
                ds18b20 = i
                readTemperatureFile(ds18b20)

    except (OSError, ValueError, RuntimeError) as error:
        log.error(f"In captureTemperature(). Error loading devices: {error}")


def readTemperatureFile(ds18b20):
    try:        
        location = sysDevicesPath + ds18b20 + temperatureDeviceName
        tfile = open(location)
        text = tfile.read()
        tfile.close()
        secondline = text.split("\n")[1]
        temperaturedata = secondline.split(" ")[9]
        temperature = float(temperaturedata[2:])
        celsius = temperature / 1000
        #farenheit = (celsius * 1.8) + 32

    except (OSError, ValueError, RuntimeError) as error:
        log.error(f"In readTemperatureFile(). Error loading temperature data: {error}")

    return celsius
