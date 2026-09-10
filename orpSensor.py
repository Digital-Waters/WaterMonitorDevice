import time

# EZO-ORP default I2C address
ATLAS_I2C_ADDRESS = 0x62


def captureORP(log):
    try:
        from smbus2 import SMBus, i2c_msg

        with SMBus(1) as bus:
            write = i2c_msg.write(ATLAS_I2C_ADDRESS, [ord('R')])
            bus.i2c_rdwr(write)
            time.sleep(0.9)  # EZO-ORP needs ~900ms for a reading

            read = i2c_msg.read(ATLAS_I2C_ADDRESS, 31)
            bus.i2c_rdwr(read)
            response = list(read)

        response_code = response[0]
        if response_code != 1:
            log.warning(f"Atlas Scientific EZO-ORP response code {response_code} — probe not ready or error.")
            return None

        data_string = ''.join(chr(b) for b in response[1:] if b != 0).strip()
        orp_mv = float(data_string)
        orp_v = round(orp_mv / 1000.0, 3)  # DB column is numeric(4,3) — store as volts
        log.info(f"ORP (EZO-ORP): {orp_mv} mV ({orp_v} V)")
        return orp_v

    except ImportError:
        log.warning("smbus2 not available; cannot read Atlas Scientific EZO-ORP probe.")
        return None
    except Exception as e:
        log.warning(f"Atlas Scientific EZO-ORP read failed: {e}")
        return None
