import time
import serial

# EZO-EC is configured for UART on this device.
# /dev/serial0 is the standard RPi serial symlink. Change to /dev/ttyUSB0
# if using a USB-UART adapter.
UART_PORT = '/dev/serial0'
BAUD_RATE = 9600


def captureConductivity(log):
    try:
        with serial.Serial(UART_PORT, BAUD_RATE, timeout=1) as ser:
            ser.reset_input_buffer()
            ser.write(b'R\r')
            time.sleep(0.6)  # EZO-EC needs ~600ms for a reading
            response = ser.readline().decode('ascii').strip()

        if not response:
            log.warning("Atlas Scientific EZO-EC: no response received on UART.")
            return None

        # Response format: EC,TDS,SAL,SG — return EC value in uS/cm
        ec = float(response.split(',')[0])
        log.info(f"Conductivity (EZO-EC): {ec} uS/cm")
        return ec

    except ImportError:
        log.warning("pyserial not available; cannot read Atlas Scientific EZO-EC probe.")
        return None
    except Exception as e:
        log.warning(f"Atlas Scientific EZO-EC read failed: {e}")
        return None
