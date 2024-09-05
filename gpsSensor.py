import serial
import pynmea2
from datetime import datetime, timedelta
import pytz

def getLoc(log):
    # This serial endpoint is for USB connection on my Pi; would be different on the RX pins
    try: 
        gpsSerial = serial.Serial('/dev/ttyACM1', baudrate=9600, timeout=1)
    except Exception as e:
        log.error(f"in GPS, error getting device: {e}")
        return False

    location = None

    try:
        while True:    
            line = gpsSerial.readline().decode('ascii', errors='replace').strip()

            # Check if the line contains a GLL sentence (you can also use GGA, RMC, etc.)
            if line.startswith('$GPGLL'):
                try:
                    # Parse the NMEA sentence
                    msg = pynmea2.parse(line)
                    
                    # Extract latitude and longitude
                    latitude = msg.latitude
                    longitude = msg.longitude

                    # Store latitude and longitude in a dictionary
                    location = {
                        "longitude": longitude,
                        "latitude": latitude
                    }

                    # Break the loop if location is successfully retrieved
                    log.info(f"In GPS location, successfully recieved data: {location}")
                    break

                except pynmea2.ParseError as e:
                    log.error(f"In GPS, Error parsing data: {e}")
                    return False
    except Exception as e:
        log.error(f"In GPS error getting data: {e}")
        return False

    except KeyboardInterrupt:
        gpsSerial.close()
        quit

    finally:
        gpsSerial.close()
        return location

def getGPSTime(log):
    try: 
        gpsSerial = serial.Serial('/dev/ttyACM0', baudrate=9600, timeout=1)
    except Exception as e:
        log.error(f"in GPS, error getting device: {e}")
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

                    log.info(f"In GPS DateTime, successfully recieved data: {localTime}")
                    break

                except pynmea2.ParseError as e:
                    log.error(f"In GPS DateTime, Error parsing data: {e}")
                    return False

    except Exception as e:
        log.error(f"In GPS DateTime error getting data: {e}")
        return False

    except KeyboardInterrupt:
        gpsSerial.close()
        quit

    finally:
        gpsSerial.close()
        return str(localTime)
