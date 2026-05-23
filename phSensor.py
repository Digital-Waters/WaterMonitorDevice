import time

# EZO-pH default I2C address
ATLAS_I2C_ADDRESS = 0x63


def capturepH(log):
    try:
        from smbus2 import SMBus, i2c_msg

        with SMBus(1) as bus:
            write = i2c_msg.write(ATLAS_I2C_ADDRESS, [ord('R')])
            bus.i2c_rdwr(write)
            time.sleep(0.9)  # EZO-pH needs ~900ms for a reading

            read = i2c_msg.read(ATLAS_I2C_ADDRESS, 31)
            bus.i2c_rdwr(read)
            response = list(read)

        response_code = response[0]
        if response_code != 1:
            log.warning(f"Atlas Scientific EZO-pH response code {response_code} — probe not ready or error.")
            return None

        data_string = ''.join(chr(b) for b in response[1:] if b != 0).strip()
        ph = float(data_string)
        log.info(f"pH (EZO-pH): {ph}")
        return ph

    except ImportError:
        log.warning("smbus2 not available; cannot read Atlas Scientific EZO-pH probe.")
        return None
    except Exception as e:
        log.warning(f"Atlas Scientific EZO-pH read failed: {e}")
        return None
