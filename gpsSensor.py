import serial
import pynmea2

def getLoc(log):
    # This serial endpoint is for USB connection on my Pi; would be different on the RX pins
    try: 
        gpsSerial = serial.Serial('/dev/ttyACM0', baudrate=9600, timeout=1)
    except Exception as e:
        log.error(f"in GPS, error getting device: {e}")
        return False

    # Initialize location with None or a default value
    location = None

    try:
        # Read lines in a loop until we get a valid GLL sentence
        
        while True:
            
            line = gpsSerial.readline().decode('ascii', errors='replace').strip()
            
            # Debugging: print the line read from the GPS

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
                    log.info(f"In GPS, successfully recieved data: {location}")
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