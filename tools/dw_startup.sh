#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# (optional) one-time debug; uncomment if you want a log
# exec >>/var/log/dw_startup.log 2>&1
# set -x

/usr/bin/tvservice -o >/dev/null 2>&1 || true
/usr/sbin/rfkill unblock wifi || true

# --- WiFi: external antenna (wlan1) is the link; wlan0 is a cold standby ------
# This device is client-only and must NEVER act as an access point.
#
# wlan0 (internal radio) is NOT left running. With both radios associated the
# unit grabs two hotspot slots and the kernel may route via wlan0; once the
# enclosure is submerged wlan0's antenna is dead, so traffic pinned to it (or to
# its IP) black-holes -- which is why the unit went silent and SSH failed
# underwater even though wlan1 was still connected. So wlan1 autoconnects and we
# only fall back to wlan0 if wlan1 cannot reach the internet (e.g. bench/setup).
#
# Credentials come from a non-committed file so they stay out of git; see
# wifi.conf.example.
WIFI_CONF="${DW_WIFI_CONF:-/home/rpi/dw/wifi.conf}"

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

wlan1_has_internet () {
    # Test connectivity *via wlan1 specifically* using its own source IP, so we
    # don't need root to bind to the interface and can't be fooled by wlan0.
    local ip
    ip="$(nmcli -g IP4.ADDRESS device show wlan1 2>/dev/null | head -n1 | cut -d/ -f1)"
    [ -n "$ip" ] || return 1
    ping -I "$ip" -c1 -W2 8.8.8.8 >/dev/null 2>&1
}

if [ -r "$WIFI_CONF" ]; then
    # shellcheck disable=SC1090
    . "$WIFI_CONF"
fi

if [ -n "${WIFI_SSID:-}" ] && [ -n "${WIFI_PSK:-}" ]; then
    # wlan1 autoconnects; wlan0 stays a manual, powered-down standby.
    ensure_wifi_profile wifi-ext wlan1 yes
    ensure_wifi_profile wifi-int wlan0 no

    /bin/ip link set wlan1 up 2>/dev/null || /usr/sbin/ip link set wlan1 up || true
    # power-save lets the radio sleep between beacons, making the device appear
    # connected but unreachable for inbound SSH/web -- keep it off on our link.
    /usr/sbin/iw dev wlan1 set power_save off || true

    # Give the external antenna up to ~45s to associate and reach the internet.
    online=0
    for _ in $(seq 1 15); do
        if wlan1_has_internet; then online=1; break; fi
        sleep 3
    done

    if [ "$online" = 1 ]; then
        # External antenna is our link -- shut the internal radio fully down so
        # it can't grab a second slot or hijack the route when submerged.
        nmcli device disconnect wlan0 >/dev/null 2>&1 || true
        /bin/ip link set wlan0 down 2>/dev/null || /usr/sbin/ip link set wlan0 down || true
        echo "dw_startup: wlan1 online; wlan0 disabled" >&2
    else
        # No internet on the external antenna -- fall back to the internal radio
        # so the device stays reachable for recovery (e.g. on the bench).
        echo "dw_startup: wlan1 offline after wait; enabling wlan0 fallback" >&2
        /bin/ip link set wlan0 up 2>/dev/null || /usr/sbin/ip link set wlan0 up || true
        /usr/sbin/iw dev wlan0 set power_save off || true
        nmcli connection up wifi-int >/dev/null 2>&1 || true
    fi
else
    echo "dw_startup: $WIFI_CONF missing or WIFI_SSID/WIFI_PSK unset; skipping wifi setup (see wifi.conf.example)" >&2
fi
# -----------------------------------------------------------------------------

exec /usr/bin/python3 /home/rpi/dw/mainloop.py
