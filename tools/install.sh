#!/usr/bin/env bash
# install.sh -- one-shot provisioner for a Digital Waters monitoring device.
#
# What it does (idempotently -- safe to re-run to repair or upgrade a device):
#   1. Installs system + Python dependencies.
#   2. Installs the Arducam Pivariety camera stack (driver + libcamera).
#   3. Applies the persistent wifi hardening (power-save off, onboard radio off),
#      and builds the AIC8800 driver if an AIC8800-based USB adapter is present.
#   4. Copies the device code into the working dir (/home/rpi/dw).
#   5. Installs and enables the systemd services one consistent way.
#
# It NEVER overwrites device-specific secrets: an existing waterMonitor.ini or
# wifi.conf is left exactly as-is (only seeded from a template if missing).
#
# Usage, from a checkout of this repo on the device:
#   sudo bash tools/install.sh
# (Re-execs itself under sudo if you forget. Set INSTALL_CAMERA=0 to skip the
#  camera step on a device with no camera attached. Set KEEP_ONBOARD_WIFI=1 to
#  leave the onboard radio on as a fallback instead of disabling it.)

set -euo pipefail

# --- re-exec as root if needed ----------------------------------------------
if [ "$(id -u)" -ne 0 ]; then
    echo "install: elevating with sudo..."
    exec sudo -E bash "$0" "$@"
fi

# --- configuration ----------------------------------------------------------
DW_USER="${DW_USER:-rpi}"                      # the unprivileged service user
DW_HOME="$(getent passwd "$DW_USER" | cut -d: -f6)"
DW_HOME="${DW_HOME:-/home/$DW_USER}"
DW_DIR="$DW_HOME/dw"                            # where the code runs on the device

# This script lives in <repo>/tools/install.sh; derive the repo root from that
# so it works regardless of where the repo was cloned.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Runtime files copied into $DW_DIR. Sensor modules live at the repo root; the
# two runtime scripts live in tools/. Dev-only helpers in tools/ are NOT
# deployed.
TOOLS_RUNTIME=(dw_startup.sh dw_netwatch.sh)

# systemd units installed into /etc/systemd/system (real copies -- one pattern).
UNITS=(dw_monitor.service dw_netwatch.service dw_netwatch.timer)
UNITS_TO_ENABLE=(dw_monitor.service dw_netwatch.timer)

# Dependencies. Keep in sync with the code's imports; a requirements.txt in the
# repo, if present, takes precedence over PIP_PKGS.
#   picamera2 + libcamera + PIL -> cameraSensor.py   spidev -> SPI sensor board
#   smbus2 -> Atlas EZO probes   requests/toolbelt -> payload.py
APT_PKGS=(python3 python3-pip git wget rfkill python3-picamera2 python3-pil python3-spidev)
PIP_PKGS=(requests requests-toolbelt smbus2)

# Arducam Pivariety camera. The distro's libcamera-apps does NOT drive this
# camera -- it needs Arducam's own libcamera build + kernel driver. We invoke
# Arducam's official installer rather than reproduce it, because the exact .deb
# set is kernel/OS-version specific and the vendor script resolves that.
# Mirrors: https://docs.arducam.com/Raspberry-Pi-Camera/Pivariety-Camera/Quick-Start-Guide/
INSTALL_CAMERA="${INSTALL_CAMERA:-1}"
ARDUCAM_SCRIPT_URL="https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/install_script/install_pivariety_pkgs.sh"
ARDUCAM_PKGS=(libcamera libcamera_apps kernel_driver)

# AIC8800 USB wifi adapters (cheap "AX300" WiFi 6 nanos, e.g. the AX5L). No
# in-kernel driver on our images, so we build the out-of-tree DKMS one. Pinned
# to a reviewed commit; its install.sh also adds the udev rule that ejects the
# adapter's fake driver CD-ROM so the wifi device appears.
# INSTALL_AIC8800=auto builds it only when such an adapter is plugged in.
INSTALL_AIC8800="${INSTALL_AIC8800:-auto}"
AIC8800_REPO="https://github.com/Kiborgik/aic8800dc-linux-patched.git"
AIC8800_COMMIT="e0242ec"                       # 6.4.3.0-patched.16
AIC8800_SRC="/usr/local/src/aic8800dc"
# USB IDs: mass-storage (pre-eject) mode, then the wifi IDs the driver handles.
AIC8800_USB_IDS="a69c:5721|a69c:5722|a69c:572a|a69c:88d[cde]|368b:88d[ef]|2357:0147|2604:001[34]|2c4e:0114|3625:0110"

# Leave the onboard radio enabled as a fallback (default: disable it). The
# external adapter is then pinned to the name wlanext and given a lower dhcpcd
# route metric so it is preferred.
KEEP_ONBOARD_WIFI="${KEEP_ONBOARD_WIFI:-0}"
WLANEXT_METRIC=200                             # dhcpcd default for wifi is 300+

# Boot config path moved in Bookworm; support both. Used by camera + wifi steps.
BOOT_CFG="/boot/firmware/config.txt"
[ -f "$BOOT_CFG" ] || BOOT_CFG="/boot/config.txt"
REBOOT_NEEDED=0
CAMERA_OK=1

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }   # bold section header
info() { printf '   %s\n' "$*"; }

# Append a line to the boot config only if it isn't already there.
ensure_boot_line() {   # $1=exact line  $2=comment
    local line="$1" comment="$2"
    if ! grep -qxF "$line" "$BOOT_CFG"; then
        printf '\n# Digital Waters: %s\n%s\n' "$comment" "$line" >> "$BOOT_CFG"
        info "added '$line' to $BOOT_CFG (takes effect after reboot)"
        REBOOT_NEEDED=1
    fi
}

install_camera() {
    # Idempotent: skip the heavy vendor install if the camera already works.
    if command -v libcamera-hello >/dev/null 2>&1 \
        && libcamera-hello --list-cameras 2>/dev/null | grep -qi pivariety; then
        info "arducam-pivariety camera already installed and detected; skipping"
        return 0
    fi
    local work pkg
    work="$(mktemp -d)"
    info "downloading Arducam installer"
    if ! wget -q -O "$work/install_pivariety_pkgs.sh" "$ARDUCAM_SCRIPT_URL"; then
        info "WARNING: could not download Arducam installer; skipping camera"
        CAMERA_OK=0; rm -rf "$work"; return 0
    fi
    chmod +x "$work/install_pivariety_pkgs.sh"
    for pkg in "${ARDUCAM_PKGS[@]}"; do
        info "arducam: installing -p $pkg"
        # </dev/null so an unattended run can't hang on a prompt; don't let a
        # vendor-script non-zero exit abort the whole provisioning run.
        if ! ( cd "$work" && ./install_pivariety_pkgs.sh -p "$pkg" </dev/null ); then
            info "WARNING: 'install_pivariety_pkgs.sh -p $pkg' failed"
            CAMERA_OK=0
        fi
    done
    rm -rf "$work"
    # The vendor script adds the overlay itself, but pin it so the camera comes
    # up on reboot regardless of which vendor code path ran.
    ensure_boot_line "dtoverlay=arducam-pivariety" "Arducam Pivariety camera"
}

install_aic8800() {
    # Capture before grepping: `cmd | grep -q` under pipefail can report a miss
    # when grep exits early and cmd dies of SIGPIPE.
    local usb dkms_state
    [ "$INSTALL_AIC8800" = "0" ] && return 0
    usb="$(lsusb 2>/dev/null || true)"
    if [ "$INSTALL_AIC8800" = "auto" ] && ! grep -qiE "ID ($AIC8800_USB_IDS) " <<<"$usb"; then
        info "no AIC8800 USB adapter detected; skipping driver (INSTALL_AIC8800=1 to force)"
        return 0
    fi
    # Idempotent: the DKMS build takes ~15 min on a Zero 2 W, so skip it when
    # the module is already installed for the running kernel.
    dkms_state="$(dkms status -m aic8800dc -k "$(uname -r)" 2>/dev/null || true)"
    if grep -q installed <<<"$dkms_state"; then
        info "aic8800dc driver already installed for $(uname -r); skipping"
        return 0
    fi
    # Bookworm ships linux-headers-<release>; Bullseye has one meta package.
    apt-get install -y dkms build-essential bc eject
    apt-get install -y "linux-headers-$(uname -r)" 2>/dev/null \
        || apt-get install -y raspberrypi-kernel-headers
    if [ ! -d "$AIC8800_SRC/.git" ]; then
        git clone -q "$AIC8800_REPO" "$AIC8800_SRC"
    fi
    git -C "$AIC8800_SRC" fetch -q origin
    git -C "$AIC8800_SRC" checkout -q "$AIC8800_COMMIT"
    info "building aic8800dc driver (slow on a Zero 2 W, ~15 min)"
    ( cd "$AIC8800_SRC" && ./install.sh )
}

# --- 1. dependencies --------------------------------------------------------
say "Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y "${APT_PKGS[@]}"

say "Installing Python packages (as $DW_USER)"
if [ -f "$REPO_DIR/requirements.txt" ]; then
    info "using requirements.txt"
    sudo -u "$DW_USER" python3 -m pip install --user -r "$REPO_DIR/requirements.txt"
else
    # --break-system-packages is needed on PEP-668 images (Bookworm+); the plain
    # install works on older (Bullseye) devices, so try it first.
    sudo -u "$DW_USER" python3 -m pip install --user "${PIP_PKGS[@]}" \
        || sudo -u "$DW_USER" python3 -m pip install --user --break-system-packages "${PIP_PKGS[@]}"
fi

# --- 2. camera --------------------------------------------------------------
if [ "$INSTALL_CAMERA" = "1" ]; then
    say "Installing Arducam Pivariety camera stack"
    install_camera
else
    say "Skipping camera install (INSTALL_CAMERA=0)"
fi

# --- 3. wifi hardening (persistent) -----------------------------------------
say "Applying wifi hardening"
install -m 0644 "$SCRIPT_DIR/8821cu.conf" /etc/modprobe.d/8821cu.conf
info "installed /etc/modprobe.d/8821cu.conf (power-save off)"
install_aic8800
if [ "$KEEP_ONBOARD_WIFI" = "1" ]; then
    # Two radios: pin the external one's name, then prefer it by route metric.
    info "KEEP_ONBOARD_WIFI=1: leaving the onboard radio enabled as a fallback"
    if ! cmp -s "$SCRIPT_DIR/10-wlanext.link" /etc/systemd/network/10-wlanext.link; then
        install -m 0644 "$SCRIPT_DIR/10-wlanext.link" /etc/systemd/network/10-wlanext.link
        info "installed /etc/systemd/network/10-wlanext.link (USB adapter -> wlanext)"
        REBOOT_NEEDED=1
    fi
    if grep -qx "interface wlanext" /etc/dhcpcd.conf 2>/dev/null; then
        info "dhcpcd.conf already prefers wlanext"
    elif [ -f /etc/dhcpcd.conf ]; then
        printf '\n# Digital Waters: prefer the external USB antenna over the onboard radio.\ninterface wlanext\nmetric %s\n' \
            "$WLANEXT_METRIC" >> /etc/dhcpcd.conf
        info "set wlanext route metric $WLANEXT_METRIC in /etc/dhcpcd.conf"
        REBOOT_NEEDED=1
    else
        info "WARNING: no /etc/dhcpcd.conf (NetworkManager device?); set the wlanext route metric by hand"
    fi
    if grep -qxF "dtoverlay=disable-wifi" "$BOOT_CFG"; then
        info "WARNING: $BOOT_CFG still has dtoverlay=disable-wifi; remove it to keep the onboard radio"
    fi
else
    # External USB antenna only: disable the onboard radio.
    ensure_boot_line "dtoverlay=disable-wifi" "external USB antenna only; disable onboard radio"
fi

# --- 4. device code ---------------------------------------------------------
say "Copying device code into $DW_DIR"
install -d -o "$DW_USER" -g "$DW_USER" "$DW_DIR" "$DW_DIR/payload" "$DW_DIR/images"

# Sensor modules + main loop (every *.py at the repo root).
for f in "$REPO_DIR"/*.py; do
    install -m 0644 -o "$DW_USER" -g "$DW_USER" "$f" "$DW_DIR/"
done
# Runtime scripts from tools/.
for f in "${TOOLS_RUNTIME[@]}"; do
    install -m 0755 -o "$DW_USER" -g "$DW_USER" "$SCRIPT_DIR/$f" "$DW_DIR/"
done
info "copied $(ls -1 "$REPO_DIR"/*.py | wc -l) python modules + ${#TOOLS_RUNTIME[@]} runtime scripts"

# Seed the config template ONLY if the device has none -- never clobber real
# credentials on an already-provisioned device.
if [ ! -f "$DW_DIR/waterMonitor.ini" ]; then
    install -m 0600 -o "$DW_USER" -g "$DW_USER" "$REPO_DIR/waterMonitor.ini" "$DW_DIR/waterMonitor.ini"
    info "seeded waterMonitor.ini template -- EDIT IT with this device's real apikey/accountnumber"
else
    info "keeping existing waterMonitor.ini (not overwritten)"
fi

# --- 5. systemd services ----------------------------------------------------
say "Installing systemd services"
for u in "${UNITS[@]}"; do
    if [ -f "$SCRIPT_DIR/$u" ]; then
        install -m 0644 "$SCRIPT_DIR/$u" "/etc/systemd/system/$u"
        info "installed $u"
    else
        info "WARNING: $u not found in tools/ -- skipping"
    fi
done
systemctl daemon-reload
for u in "${UNITS_TO_ENABLE[@]}"; do
    systemctl enable --now "$u"
    info "enabled + started $u"
done

# --- summary ----------------------------------------------------------------
say "Done. Service status:"
for u in "${UNITS_TO_ENABLE[@]}"; do
    printf '   %-30s %s / %s\n' "$u" \
        "$(systemctl is-enabled "$u" 2>/dev/null || echo '?')" \
        "$(systemctl is-active "$u" 2>/dev/null || echo '?')"
done
echo
[ "$INSTALL_CAMERA" = "1" ] && [ "$CAMERA_OK" -ne 1 ] && \
    echo "   NOTE: the camera install reported problems -- re-run and watch its output."
if [ "$REBOOT_NEEDED" -eq 1 ]; then
    echo "   NOTE: a reboot is required for boot/network config changes (camera overlay,"
    echo "         onboard radio, or wlanext naming). Run: sudo reboot"
fi
if grep -q 'YOUR_API_KEY_HERE' "$DW_DIR/waterMonitor.ini" 2>/dev/null; then
    echo "   NOTE: $DW_DIR/waterMonitor.ini still has placeholder credentials -- edit it."
fi
