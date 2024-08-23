import serial
import time

def read_gps():
    # Set up serial connection to GPS module
    gps_serial = serial.Serial('/dev/serial0', baudrate=9600, timeout=1)
    time.sleep(2)  # Allow the connection to stabilize

    while True:
        line = gps_serial.readline().decode('utf-8', errors='replace')
        if line.startswith('$GPGGA'):
            print(line)
            # Additional parsing logic can be added here

if __name__ == "__main__":
    read_gps()
