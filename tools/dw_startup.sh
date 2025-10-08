#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# (optional) one-time debug; uncomment if you want a log
# exec >>/var/log/dw_startup.log 2>&1
# set -x

/usr/bin/tvservice -o >/dev/null 2>&1 || true
/usr/sbin/rfkill unblock wifi || true
/bin/ip link set wlan0 up || /usr/sbin/ip link set wlan0 up || true
/usr/sbin/iw dev wlan0 set power_save on || true

exec /usr/bin/python3 /home/rpi/dw/mainloop.py
