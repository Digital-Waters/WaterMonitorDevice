import time

import sensorHealth

# EZO-EC default I2C address
ATLAS_I2C_ADDRESS = 0x64

# Health of the latest read, reported in the device status (see sensorHealth).
lastStatus = None


def _setTemperatureCompensation(bus, i2c_msg, temp_c, log):
    """Send T,<temp_c> to the circuit. Returns True if it was accepted."""
    command = f"T,{temp_c:.2f}"
    bus.i2c_rdwr(i2c_msg.write(ATLAS_I2C_ADDRESS, list(command.encode('ascii'))))
    time.sleep(0.3)  # EZO-EC needs ~300ms to process the T command

    read = i2c_msg.read(ATLAS_I2C_ADDRESS, 31)
    bus.i2c_rdwr(read)
    response_code = list(read)[0]
    if response_code != 1:
        log.warning(f"Atlas Scientific EZO-EC rejected temperature compensation (code {response_code}).")
    return response_code == 1


def captureConductivity(log, temp_c=None):
    global lastStatus
    try:
        from smbus2 import SMBus, i2c_msg

        with SMBus(1) as bus:
            # Send the water temperature so the circuit reports conductivity normalized to 25 C.
            # The circuit keeps the last value it was sent until it loses power,
            # so with no temperature this cycle we send 25 C (no correction)
            # rather than let it reuse an old one. Data rule: a record with a
            # water temperature has a corrected reading; one without is unadjusted.
            compensated = temp_c is not None
            if not compensated:
                log.warning("No water temperature available; EZO-EC reading is unadjusted (circuit reset to 25 C).")
            if not _setTemperatureCompensation(bus, i2c_msg, temp_c if compensated else 25.0, log):
                # The reading would break the data rule above, so drop it.
                lastStatus = sensorHealth.error("temperature compensation rejected")
                return None

            write = i2c_msg.write(ATLAS_I2C_ADDRESS, [ord('R')])
            bus.i2c_rdwr(write)
            time.sleep(0.6)  # EZO-EC needs ~600ms for a reading

            read = i2c_msg.read(ATLAS_I2C_ADDRESS, 31)
            bus.i2c_rdwr(read)
            response = list(read)

        response_code = response[0]
        if response_code != 1:
            log.warning(f"Atlas Scientific EZO-EC response code {response_code} — probe not ready or error.")
            lastStatus = sensorHealth.error(f"response code {response_code}")
            return None

        # Response format: EC,TDS,SAL,SG — return EC value in uS/cm
        data_string = ''.join(chr(b) for b in response[1:] if b != 0).strip()
        ec = float(data_string.split(',')[0])
        log.info(f"Conductivity (EZO-EC): {ec} uS/cm")
        lastStatus = sensorHealth.ok(tempCompensated=compensated)
        return ec

    except ImportError:
        log.warning("smbus2 not available; cannot read Atlas Scientific EZO-EC probe.")
        lastStatus = sensorHealth.error("smbus2 not installed")
        return None
    except Exception as e:
        log.warning(f"Atlas Scientific EZO-EC read failed: {e}")
        lastStatus = sensorHealth.fromI2CException(e)
        return None
