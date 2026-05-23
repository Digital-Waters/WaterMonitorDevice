import time

# EZO-EC default I2C address. If this probe is configured for UART mode,
# this file will not work — switch the circuit to I2C mode first.
ATLAS_I2C_ADDRESS = 0x64


def captureConductivity(log):
    try:
        from smbus2 import SMBus, i2c_msg

        with SMBus(1) as bus:
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

        # Response format: EC,TDS,SAL,SG — return EC value in μS/cm
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
