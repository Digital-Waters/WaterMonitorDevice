import serial
import pynmea2
from datetime import datetime, timedelta
import pytz

def getLoc(log):
    # This serial endpoint is for USB connection on my Pi; would be different on the RX pins
    try: 
        gpsSerial = serial.Serial('/dev/serial0', baudrate=9600, timeout=1)
    except Exception as e:
        log.error(f"in GPS, error getting device: {e}")
        return False

    location = None

    try:
        while True:    
            line = gpsSerial.readline().decode('ascii', errors='replace').strip()
            # Check if the line contains a GLL sentence (you can also use GGA, RMC, etc.)
            if line.startswith('$GPRMC'):
                try:
                    msg = pynmea2.parse(line)
                    if msg.status == 'A': 
                        latitude = msg.latitude
                        longitude = msg.longitude
                        location = {"longitude": longitude, "latitude": latitude}
                        log.info(f"In getLoc, successfully received data: {location}")
                        break
                    else:
                        log.info("In getLoc, GPS data is invalid.")
                        break
                except pynmea2.ParseError as e:
                    log.error(f"In getLoc, Error parsing data: {e}")
                    return False

    except Exception as e:
        log.error(f"In getLoc error getting data: {e}")
        return False

    except KeyboardInterrupt:
        gpsSerial.close()
        quit

    finally:
        gpsSerial.close()
        return location

def getGPSTime(log, timeZone):
    try: 
        gpsSerial = serial.Serial('/dev/serial0', baudrate=9600, timeout=1)
    except Exception as e:
        log.error(f"in getGPSTime, error getting device: {e}")
        return False
    
    localTime = None
    try:
        while True:
            line = gpsSerial.readline().decode('ascii', errors='replace').strip()
            
            if line.startswith('$GPRMC'):  # Recommended Minimum data for GPS
                try:
                    msg = pynmea2.parse(line)
                    gpsTime = msg.timestamp  # UTC time
                    gpsDate = msg.datestamp  # UTC date

                    # Combine date and time
                    utcTime = datetime.combine(gpsDate, gpsTime)

                    # Convert UTC to EST/EDT based on current rules
                    timezone = pytz.timezone('America/Toronto')
                    localTime = utcTime.replace(tzinfo=pytz.utc).astimezone(timezone)

                    log.info(f"In getGPSTime DateTime, successfully recieved data: {localTime}")
                    break

                except pynmea2.ParseError as e:
                    log.error(f"In getGPSTime DateTime, Error parsing data: {e}")
                    return False

    except Exception as e:
        log.error(f"In getGPSTime DateTime error getting data: {e}")
        return False

    except KeyboardInterrupt:
        gpsSerial.close()
        quit

    finally:
        gpsSerial.close()
        return str(localTime)
