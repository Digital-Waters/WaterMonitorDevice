import time

# EZO-EC default I2C address
ATLAS_I2C_ADDRESS = 0x64


def _setTemperatureCompensation(bus, i2c_msg, temp_c, log):
    command = f"T,{temp_c:.2f}"
    bus.i2c_rdwr(i2c_msg.write(ATLAS_I2C_ADDRESS, list(command.encode('ascii'))))
    time.sleep(0.3)  # EZO-EC needs ~300ms to process the T command

    read = i2c_msg.read(ATLAS_I2C_ADDRESS, 31)
    bus.i2c_rdwr(read)
    response_code = list(read)[0]
    if response_code != 1:
        log.warning(f"Atlas Scientific EZO-EC rejected temperature compensation (code {response_code}).")


def captureConductivity(log, temp_c=None):
    try:
        from smbus2 import SMBus, i2c_msg

        with SMBus(1) as bus:
            # Send the water temperature so the circuit reports conductivity
            # normalized to 25 C (specific conductance). Without it the circuit
            # assumes the water is already 25 C. Sent every cycle because the
            # circuit does not keep it across power loss.
            if temp_c is not None:
                _setTemperatureCompensation(bus, i2c_msg, temp_c, log)
            else:
                log.warning("No water temperature available; EZO-EC reading is not temperature compensated.")

            write = i2c_msg.write(ATLAS_I2C_ADDRESS, [ord('R')])
            bus.i2c_rdwr(write)
            time.sleep(0.6)  # EZO-EC needs ~600ms for a reading

            read = i2c_msg.read(ATLAS_I2C_ADDRESS, 31)
            bus.i2c_rdwr(read)
            response = list(read)

        response_code = response[0]
        if response_code != 1:
            log.warning(f"Atlas Scientific EZO-EC response code {response_code} — probe not ready or error.")
            return None

        # Response format: EC,TDS,SAL,SG — return EC value in uS/cm
        data_string = ''.join(chr(b) for b in response[1:] if b != 0).strip()
        ec = float(data_string.split(',')[0])
        log.info(f"Conductivity (EZO-EC): {ec} uS/cm")
        return ec

    except ImportError:
        log.warning("smbus2 not available; cannot read Atlas Scientific EZO-EC probe.")
        return None
    except Exception as e:
        log.warning(f"Atlas Scientific EZO-EC read failed: {e}")
        return None
