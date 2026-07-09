#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# (optional) one-time debug; uncomment if you want a log
# exec >>/var/log/dw_startup.log 2>&1
# set -x

/usr/bin/tvservice -o >/dev/null 2>&1 || true
/usr/sbin/rfkill unblock wifi || true

# Bring up both radios. wlan1 = external antenna (preferred; the only usable
# link when the enclosure is submerged). wlan0 = internal radio (backup).
/bin/ip link set wlan0 up 2>/dev/null || /usr/sbin/ip link set wlan0 up || true
/bin/ip link set wlan1 up 2>/dev/null || /usr/sbin/ip link set wlan1 up || true

# Keep the external antenna responsive to *inbound* connections (SSH/web):
# power-save lets the radio sleep between beacons, which makes the device
# appear connected but unreachable. Leave the internal backup radio saving power.
/usr/sbin/iw dev wlan1 set power_save off || true
/usr/sbin/iw dev wlan0 set power_save on  || true

# --- WiFi client provisioning (idempotent, runs every boot) ------------------
# This device is client-only and must NEVER act as an access point. It joins one
# network on two interfaces, preferring the external antenna. Credentials are
# read from a non-committed file so they stay out of git; see wifi.conf.example.
WIFI_CONF="${DW_WIFI_CONF:-/home/rpi/dw/wifi.conf}"

ensure_wifi_profile () {
    # $1=connection name  $2=interface  $3=autoconnect-priority (higher wins)
    local con="$1" ifname="$2" prio="$3"
    if nmcli -t -g NAME connection show 2>/dev/null | grep -qx "$con"; then
        nmcli connection modify "$con" \
            connection.interface-name "$ifname" \
            802-11-wireless.ssid "$WIFI_SSID" \
            wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$WIFI_PSK" \
            connection.autoconnect yes \
            connection.autoconnect-priority "$prio" \
            connection.autoconnect-retries 0 || true
    else
        nmcli connection add type wifi con-name "$con" ifname "$ifname" ssid "$WIFI_SSID" \
            wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$WIFI_PSK" \
            connection.autoconnect yes \
            connection.autoconnect-priority "$prio" \
            connection.autoconnect-retries 0 || true
    fi
}

if [ -r "$WIFI_CONF" ]; then
    # shellcheck disable=SC1090
    . "$WIFI_CONF"
    if [ -n "${WIFI_SSID:-}" ] && [ -n "${WIFI_PSK:-}" ]; then
        ensure_wifi_profile wifi-ext wlan1 20   # external antenna, preferred
        ensure_wifi_profile wifi-int wlan0 10   # internal radio, backup
    else
        echo "dw_startup: $WIFI_CONF present but WIFI_SSID/WIFI_PSK unset; skipping wifi provisioning" >&2
    fi
else
    echo "dw_startup: $WIFI_CONF not found; skipping wifi provisioning (see wifi.conf.example)" >&2
fi
# -----------------------------------------------------------------------------

exec /usr/bin/python3 /home/rpi/dw/mainloop.py
