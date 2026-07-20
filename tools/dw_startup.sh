#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# (optional) one-time debug; uncomment if you want a log
# exec >>/var/log/dw_startup.log 2>&1
# set -x

/usr/bin/tvservice -o >/dev/null 2>&1 || true
/usr/sbin/rfkill unblock wifi || true

# --- WiFi: external antenna only; the internal radio is disabled outright -----
# This device is client-only and must NEVER act as an access point.
#
# The internal radio's antenna is dead once the enclosure is submerged, and any
# time it is associated the kernel may pin routes (or inbound SSH) to it, which
# black-holes underwater. Earlier revisions kept it as a fallback behind an
# internet check, but that check raced the external link at boot (and could be
# satisfied via the internal radio's own route), so one bad boot left the
# internal radio up for the whole deployment. The rule is now unconditional:
# if the external USB adapter is present, the internal radio is shut down and
# marked unmanaged so NetworkManager cannot bring it back. The internal radio
# is only used when the USB adapter is missing altogether (bench recovery with
# the enclosure open).
#
# Interfaces are identified by bus, not name: the onboard radio is SDIO, the
# antenna adapter is USB. wlan0/wlan1 assignment can vary, and disabling the
# onboard radio via dtoverlay=disable-wifi renames the USB adapter to wlan0,
# so names are never hard-coded.
#
# Credentials come from a non-committed file so they stay out of git; see
# wifi.conf.example.
WIFI_CONF="${DW_WIFI_CONF:-/home/rpi/dw/wifi.conf}"

INT_IF="" EXT_IF=""
for path in /sys/class/net/wlan*; do
    [ -e "$path/device" ] || continue
    if readlink -f "$path/device" | grep -q usb; then
        EXT_IF="${path##*/}"
    else
        INT_IF="${path##*/}"
    fi
done

ensure_wifi_profile () {
    # $1=connection name  $2=interface  $3=autoconnect (yes|no)
    local con="$1" ifname="$2" auto="$3"
    if nmcli -t -g NAME connection show 2>/dev/null | grep -qx "$con"; then
        nmcli connection modify "$con" \
            connection.interface-name "$ifname" \
            802-11-wireless.ssid "$WIFI_SSID" \
            wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$WIFI_PSK" \
            connection.autoconnect "$auto" \
            connection.autoconnect-retries 0 || true
    else
        nmcli connection add type wifi con-name "$con" ifname "$ifname" ssid "$WIFI_SSID" \
            wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$WIFI_PSK" \
            connection.autoconnect "$auto" \
            connection.autoconnect-retries 0 || true
    fi
}

disable_other_wifi_profiles () {
    # Any wifi profile other than $1 (e.g. the imager's "preconfigured" one is
    # not bound to an interface) could still autoconnect the internal radio.
    local keep="$1" con
    nmcli -t -f NAME,TYPE connection show 2>/dev/null |
        awk -F: -v keep="$keep" '$2 ~ /wireless/ && $1 != keep {print $1}' |
        while IFS= read -r con; do
            nmcli connection modify "$con" connection.autoconnect no || true
        done || true
}

if [ -r "$WIFI_CONF" ]; then
    # shellcheck disable=SC1090
    . "$WIFI_CONF"
fi

if [ -z "${WIFI_SSID:-}" ] || [ -z "${WIFI_PSK:-}" ]; then
    echo "dw_startup: $WIFI_CONF missing or WIFI_SSID/WIFI_PSK unset; skipping wifi setup (see wifi.conf.example)" >&2
elif [ -n "$EXT_IF" ]; then
    ensure_wifi_profile wifi-ext "$EXT_IF" yes
    disable_other_wifi_profiles wifi-ext

    ip link set "$EXT_IF" up 2>/dev/null || true
    # power-save lets the radio sleep between beacons, making the device appear
    # connected but unreachable for inbound SSH/web -- keep it off on our link.
    iw dev "$EXT_IF" set power_save off || true
    nmcli connection up wifi-ext >/dev/null 2>&1 || true

    if [ -n "$INT_IF" ]; then
        nmcli device disconnect "$INT_IF" >/dev/null 2>&1 || true
        nmcli device set "$INT_IF" managed no >/dev/null 2>&1 || true
        ip link set "$INT_IF" down 2>/dev/null || true
        echo "dw_startup: external antenna $EXT_IF is the link; internal radio $INT_IF disabled" >&2
    else
        echo "dw_startup: external antenna $EXT_IF is the link; no internal radio present" >&2
    fi
elif [ -n "$INT_IF" ]; then
    # No USB adapter at all -- bench recovery on the internal radio so the
    # device stays reachable with the enclosure open.
    echo "dw_startup: no external USB adapter found; using internal radio $INT_IF" >&2
    ensure_wifi_profile wifi-int "$INT_IF" yes
    ip link set "$INT_IF" up 2>/dev/null || true
    iw dev "$INT_IF" set power_save off || true
    nmcli connection up wifi-int >/dev/null 2>&1 || true
else
    echo "dw_startup: no wifi interfaces found" >&2
fi
# -----------------------------------------------------------------------------

exec /usr/bin/python3 /home/rpi/dw/mainloop.py
