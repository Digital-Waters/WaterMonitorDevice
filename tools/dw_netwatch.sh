#!/usr/bin/env bash
# dw_netwatch.sh -- Digital Waters connectivity watchdog.
#
# Why this exists
# ---------------
# Our devices keep sampling and logging sensor data even when they fall off the
# network (payloads are buffered to disk and backfilled once the link returns).
# That is great for data integrity, but it means a wedged wifi link is INVISIBLE
# from the device's point of view -- it happily runs for days while nobody
# receives its uploads. This script is the safety net: run it on a timer, and
# when the device has been off the internet for a sustained period it nudges the
# network back to life, and reboots as a last resort.
#
# Design goals
# ------------
#  * Stack-agnostic. It does NOT care whether the link is managed by
#    wpa_supplicant + dhcpcd (our fielded default) or NetworkManager. It only
#    asks "is the internet reachable?" and, if not, restarts whichever
#    networking services are actually running -- `systemctl try-restart` is a
#    no-op for units that are inactive, so we never accidentally start the wrong
#    stack.
#  * Safe. It only ever acts when the device is ALREADY offline, so it cannot
#    make a healthy device worse. Reboots are rate-limited by system uptime, so
#    it can never fall into a reboot loop.
#  * Blames the network, not our API. The reachability check targets the public
#    internet (1.1.1.1 / 8.8.8.8), NOT data.digitalwaters.org -- an outage on
#    our own server must never reboot a field device.
#
# Escalation (with the default 5-minute timer):
#   ~10 min offline  -> restart active networking services   (gentle)
#   ~60 min offline  -> reboot, once uptime allows            (last resort)
# then at most one reboot per REBOOT_MIN_UPTIME thereafter.

set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# --- configuration (override in /etc/default/dw_netwatch if you need to) -----
PING_TARGETS=("1.1.1.1" "8.8.8.8")   # general-internet check, not our API
PING_COUNT=3                          # echo requests per target
PING_TIMEOUT=5                        # seconds to wait per target
FAIL_BEFORE_RESTART=2                 # consecutive failed runs before gentle fix
FAIL_BEFORE_REBOOT=4                  # consecutive failed runs before reboot
REBOOT_MIN_UPTIME=3600                # don't reboot within this many secs of boot
NET_SERVICES=(dhcpcd wpa_supplicant NetworkManager networking systemd-networkd)
STATE_DIR=/run/dw_netwatch            # on tmpfs: the counter resets on every boot
STATE_FILE="$STATE_DIR/fail_count"

# Optional per-device overrides (e.g. a slower network wants a longer fuse).
[ -r /etc/default/dw_netwatch ] && . /etc/default/dw_netwatch

log() { echo "dw_netwatch: $*"; }     # stdout is captured by the systemd journal

# Returns 0 if any target answers, 1 if they all fail.
online() {
    local target
    for target in "${PING_TARGETS[@]}"; do
        if ping -c "$PING_COUNT" -W "$PING_TIMEOUT" "$target" >/dev/null 2>&1; then
            return 0
        fi
    done
    return 1
}

mkdir -p "$STATE_DIR"
fails=0
[ -r "$STATE_FILE" ] && fails=$(cat "$STATE_FILE" 2>/dev/null || echo 0)

# --- happy path: we're online, reset and leave -------------------------------
if online; then
    if [ "$fails" -ne 0 ]; then
        log "internet reachable again after $fails failed check(s); clearing counter"
    fi
    echo 0 > "$STATE_FILE"
    exit 0
fi

# --- offline: count the failure and escalate ---------------------------------
fails=$((fails + 1))
echo "$fails" > "$STATE_FILE"
log "internet unreachable (consecutive failed checks: $fails)"

uptime_secs=$(cut -d. -f1 /proc/uptime 2>/dev/null || echo 0)

# Last resort: reboot -- but only if we didn't just boot, so we can't loop.
if [ "$fails" -ge "$FAIL_BEFORE_REBOOT" ]; then
    if [ "$uptime_secs" -ge "$REBOOT_MIN_UPTIME" ]; then
        log "still offline after $fails checks; rebooting (uptime ${uptime_secs}s)"
        echo 0 > "$STATE_FILE"
        systemctl reboot
        exit 0
    fi
    log "would reboot but uptime ${uptime_secs}s < ${REBOOT_MIN_UPTIME}s; deferring to avoid a reboot loop"
fi

# Gentle fix: bounce whichever networking services are actually running.
if [ "$fails" -ge "$FAIL_BEFORE_RESTART" ]; then
    log "restarting any active networking services: ${NET_SERVICES[*]}"
    systemctl try-restart "${NET_SERVICES[@]}" 2>/dev/null || true
fi

exit 0
