#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# (optional) one-time debug; uncomment if you want a log
# exec >>/var/log/dw_startup.log 2>&1
# set -x

/usr/bin/tvservice -o >/dev/null 2>&1 || true
/usr/sbin/rfkill unblock wifi || true

# --- WiFi -------------------------------------------------------------------
# WiFi is intentionally NOT configured here anymore.
#
# Earlier revisions tried to (re)provision the link with nmcli at boot, but our
# fielded devices do not run NetworkManager -- they connect with the stock
# wpa_supplicant + dhcpcd stack written by the Raspberry Pi Imager. Every nmcli
# call therefore failed silently (they were all "|| true"), so the block did
# nothing while looking like it worked, and the safeguards it claimed to apply
# (power-save off, disabling the onboard radio) never took effect. That is how a
# device ended up "generating data but offline" with no way to recover.
#
# Each job the old block attempted is now owned by purpose-built, persistent
# config instead:
#
#   Join the network      -> /etc/wpa_supplicant/wpa_supplicant.conf (Imager)
#   Disable power-save     -> /etc/modprobe.d/8821cu.conf  (rtw_power_mgnt=0)
#   Disable onboard radio  -> /boot/config.txt: dtoverlay=disable-wifi
#     (external USB antenna only; also renames the USB adapter to wlan0)
#   Recover a wedged link  -> dw_netwatch.sh, run by dw_netwatch.timer
#     / stay reachable
#
# See tools/8821cu.conf, tools/dw_netwatch.* and the README for provisioning.
# ----------------------------------------------------------------------------

exec /usr/bin/python3 /home/rpi/dw/mainloop.py
