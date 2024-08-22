import serial
import pynmea2

# Set up the serial connection
gps_serial = serial.Serial('/dev/ttyACM0', baudrate=9600, timeout=1)

try:
    while True:
        line = gps_serial.readline().decode('ascii', errors='replace').strip()
        
        # Check if the line contains a GGA sentence (you can also use GLL, RMC, etc.)
        if line.startswith('$GPGLL'):
            try:
                # Parse the NMEA sentence
                msg = pynmea2.parse(line)
                
                # Extract latitude and longitude
                latitude = msg.latitude
                longitude = msg.longitude

                # Print the latitude and longitude
                print(f"Latitude: {latitude}, Longitude: {longitude}")

            except pynmea2.ParseError as e:
                print(f"Could not parse line: {line}. Error: {e}")

except KeyboardInterrupt:
    print("Program interrupted by user")

finally:
    gps_serial.close()
