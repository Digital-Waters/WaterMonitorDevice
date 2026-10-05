import os
import glob
import time

import sensorHealth

base_dir = '/sys/bus/w1/devices/'

# Health of the latest read, reported in the device status (see sensorHealth).
lastStatus = None


def _read_temp_raw(device_file):
    with open(device_file, 'r') as f:
        lines = f.readlines()
    return lines


# Each reader returns (temp_c or None, sensorHealth status).
def _read_ds18b20(log):
    try:
        device_folder = glob.glob(base_dir + '28*')[0]
        device_file = device_folder + '/w1_slave'

        lines = _read_temp_raw(device_file)
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            lines = _read_temp_raw(device_file)
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_c = float(lines[1][equals_pos + 2:]) / 1000.0
            log.info(f"Temperature (DS18B20): {temp_c} Celsius")
            return temp_c, sensorHealth.ok(source="DS18B20")
        return None, sensorHealth.error("DS18B20 returned no temperature")

    except IndexError:
        log.info("No DS18B20 sensor detected.")
        return None, sensorHealth.absent()
    except Exception as e:
        log.info(f"DS18B20 read failed: {e}")
        return None, sensorHealth.error(f"DS18B20: {e}")


def _read_atlas_rtd(log):
    # Requires the Atlas Scientific EZO-RTD circuit configured for I2C mode.
    # Default I2C address is 0x66. Requires smbus2: pip install smbus2
    ATLAS_I2C_ADDRESS = 0x66
    try:
        from smbus2 import SMBus, i2c_msg

        with SMBus(1) as bus:
            write = i2c_msg.write(ATLAS_I2C_ADDRESS, [ord('R')])
            bus.i2c_rdwr(write)
            time.sleep(1.0)  # EZO-RTD needs ~1s to complete a reading

            read = i2c_msg.read(ATLAS_I2C_ADDRESS, 31)
            bus.i2c_rdwr(read)
            response = list(read)

        response_code = response[0]
        if response_code != 1:
            log.warning(f"Atlas Scientific RTD response code {response_code} — probe not ready or error.")
            return None, sensorHealth.error(f"EZO-RTD response code {response_code}")

        temp_string = ''.join(chr(b) for b in response[1:] if b != 0).strip()
        temp_c = float(temp_string)
        log.info(f"Temperature (Atlas Scientific RTD): {temp_c} Celsius")
        return temp_c, sensorHealth.ok(source="EZO-RTD")

    except ImportError:
        log.warning("smbus2 not available; cannot read Atlas Scientific probe.")
        return None, sensorHealth.error("smbus2 not installed")
    except Exception as e:
        log.warning(f"Atlas Scientific RTD read failed: {e}")
        return None, sensorHealth.fromI2CException(e)


def captureTemperature(log):
    global lastStatus

    temp, dsStatus = _read_ds18b20(log)
    if temp is not None:
        lastStatus = dsStatus
        return temp

    temp, rtdStatus = _read_atlas_rtd(log)
    if temp is not None:
        lastStatus = rtdStatus
        return temp

    log.warning("No temperature probe returned a valid reading.")
    # Report a failing probe over a missing one: an error means a probe is
    # installed but broken, which is what a volunteer needs to know.
    if dsStatus["status"] == sensorHealth.ERROR:
        lastStatus = dsStatus
    elif rtdStatus["status"] == sensorHealth.ERROR:
        lastStatus = rtdStatus
    else:
        lastStatus = sensorHealth.absent()
    return None
