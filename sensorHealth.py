# Per-sensor health for the latest capture, reported to the server in each
# device status so volunteers can see which sensors are working at a glance.
#
#   ok     -> the sensor returned a reading
#   error  -> the sensor is there but the read failed (bad response, exception)
#   absent -> no sensor detected (not installed, unplugged, no I2C response)

OK = "ok"
ERROR = "error"
ABSENT = "absent"

# On the Pi, an I2C transfer to an address nothing answers on fails with
# EREMOTEIO ("Remote I/O error"). Hard-coded because errno.EREMOTEIO does not
# exist on every platform.
_EREMOTEIO = 121


def ok(**details):
    return {"status": OK, **details}


def error(detail):
    return {"status": ERROR, "detail": detail}


def absent(detail=None):
    status = {"status": ABSENT}
    if detail:
        status["detail"] = detail
    return status


def fromI2CException(e):
    """Classify an exception from an Atlas Scientific I2C read."""
    if isinstance(e, OSError) and e.errno == _EREMOTEIO:
        return absent("no response on I2C address")
    return error(str(e))
