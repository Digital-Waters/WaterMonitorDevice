import serial
import pynmea2

def getLoc():
    # This serial endpoint is for USB connection on my Pi; would be different on the RX pins
    gps_serial = serial.Serial('/dev/ttyACM0', baudrate=9600, timeout=1)
    
    # Initialize location with None or a default value
    location = None

    try:
        # Read lines in a loop until we get a valid GLL sentence
        while True:
            line = gps_serial.readline().decode('ascii', errors='replace').strip()
            
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
                    break

                except pynmea2.ParseError as e:
                    print(f"Could not parse line: {line}. Error: {e}")

    except KeyboardInterrupt:
        gps_serial.close()
        print("Program interrupted by user")
        quit
    finally:
        gps_serial.close()
        return location

