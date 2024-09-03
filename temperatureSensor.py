import os
import glob
import time

# Base directory for the sensor data
base_dir = '/sys/bus/w1/devices/'

def read_temp_raw(device_file):
    with open(device_file, 'r') as f:
        lines = f.readlines()
    return lines

def captureTemperature(log):
    try:
        # Check for the temperature sensor
        device_folder = glob.glob(base_dir + '28*')[0]
        device_file = device_folder + '/w1_slave'

        lines = read_temp_raw(device_file)
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            lines = read_temp_raw(device_file)
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0

            log.info(f"Temperature: {temp_c} Celcius")
            return temp_c

    except IndexError:
        log.info("No temperature sensor connected.")
        return None
    except Exception as e:
        log.info(f"An error occurred: {e}")
        return None
