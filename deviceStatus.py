import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone

import requests


# Device status reporting. Every time the device sends data it also POSTs a
# small status to the server, which keeps one row per device up to date for the
# admin site (sync progress + ETA, last upload, which sensors are working).
#
# syncStatus is one of:
#   realtime    -> a live capture uploaded and nothing was queued (normal check-in)
#   start       -> a live capture uploaded and a backlog sync is about to begin
#   in_progress -> periodic progress while the backlog drains
#   finished    -> the sync ended; result is "complete" or "interrupted"
#
# The device never reports "offline"; the server infers it from silence.
#
# Status reporting is best effort: a failed status POST is logged and never
# affects capture uploads or the backlog.

# Used when waterMonitor.ini has no statusURL key, so deployed devices report
# without a config edit. An explicitly blank statusURL disables reporting.
DEFAULT_STATUS_URL = "https://api.digitalwaters.org/status/"

SYNC_STATE_FILE = os.path.join("payload", "syncState.json")
STATUS_TIMEOUT_SECONDS = 10

# During a sync, send in_progress after this many records or seconds,
# whichever comes first.
PROGRESS_EVERY_RECORDS = 25
PROGRESS_EVERY_SECONDS = 30

_softwareVersion = None


def _utcNow():
    return datetime.now(timezone.utc).isoformat()


def _dropNone(d):
    return {k: v for k, v in d.items() if v is not None}


# ---------------------------------------------------------------------------
# Persistent sync state
#
# Only what cannot be derived from the backlog file lives here (lifetime count,
# last sync times). It is a separate file rather than a header line in
# payloadData.txt so that new captures stay cheap appends.
# ---------------------------------------------------------------------------

def loadSyncState(log):
    try:
        with open(SYNC_STATE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        log.warning(f"Could not read {SYNC_STATE_FILE}, starting fresh: {e}")
        return {}


def saveSyncState(state, log):
    # Write to a temp file and swap it in, so a power cut leaves either the old
    # or the new state on disk, never a half-written file.
    tmpFile = SYNC_STATE_FILE + ".tmp"
    try:
        os.makedirs(os.path.dirname(SYNC_STATE_FILE), exist_ok=True)
        with open(tmpFile, 'w') as f:
            json.dump(state, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmpFile, SYNC_STATE_FILE)
    except OSError as e:
        log.warning(f"Could not write {SYNC_STATE_FILE}: {e}")


# ---------------------------------------------------------------------------
# Device health. Every reader returns None when the value is unavailable (e.g.
# when running off-device), and None fields are left out of the status.
# ---------------------------------------------------------------------------

def _readFile(path):
    try:
        with open(path, 'r') as f:
            return f.read()
    except OSError:
        return None


def _run(args):
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=5,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _uptimeSeconds():
    text = _readFile('/proc/uptime')
    return int(float(text.split()[0])) if text else None


def _diskFreeMB():
    try:
        return shutil.disk_usage(os.path.dirname(os.path.abspath(__file__))).free // (1024 * 1024)
    except OSError:
        return None


def _cpuTempC():
    text = _readFile('/sys/class/thermal/thermal_zone0/temp')
    try:
        return round(int(text) / 1000.0, 1) if text else None
    except ValueError:
        return None


def _throttled():
    # Pi undervoltage/throttling flags, e.g. "0x0" (healthy) or "0x50005".
    out = _run(['vcgencmd', 'get_throttled'])
    return out.split('=', 1)[1] if out and '=' in out else None


def _softwareVersionString():
    # git commit of the running code; cached since it only changes on restart.
    global _softwareVersion
    if _softwareVersion is None:
        _softwareVersion = _run(['git', 'rev-parse', '--short', 'HEAD']) or ""
    return _softwareVersion or None


def _defaultRouteInterface():
    # The interface carrying the default route (wlan1 external antenna vs wlan0).
    text = _readFile('/proc/net/route')
    if not text:
        return None
    best = None
    for line in text.splitlines()[1:]:
        fields = line.split()
        if len(fields) > 6 and fields[1] == '00000000':
            metric = int(fields[6])
            if best is None or metric < best[1]:
                best = (fields[0], metric)
    return best[0] if best else None


def _wifiSignalDbm(interface):
    text = _readFile('/proc/net/wireless')
    if not text or not interface:
        return None
    for line in text.splitlines()[2:]:
        name, _, rest = line.partition(':')
        if name.strip() == interface:
            fields = rest.split()
            try:
                return int(float(fields[2]))
            except (IndexError, ValueError):
                return None
    return None


def collectHealth():
    interface = _defaultRouteInterface()
    return _dropNone({
        "softwareVersion": _softwareVersionString(),
        "uptimeSec": _uptimeSeconds(),
        "diskFreeMB": _diskFreeMB(),
        "cpuTempC": _cpuTempC(),
        "throttled": _throttled(),
        "networkInterface": interface,
        "wifiSignalDbm": _wifiSignalDbm(interface),
    })


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------

class StatusReporter:
    """Sends the status for one capture cycle: either a single realtime
    check-in, or start -> in_progress... -> finished around a backlog sync.

    lastCapture is {"captureDateTime": ..., "sensors": {...}} for the live
    capture that triggered this cycle. deviceConfig is the device's current
    settings (e.g. {"sleepIntervalSec": 300}); the server uses sleepIntervalSec
    to decide when a silent device counts as offline.
    """

    def __init__(self, session, secrets, log, deviceCode, lastCapture, deviceConfig=None):
        self.session = session
        self.log = log
        self.deviceCode = deviceCode
        self.lastCapture = lastCapture
        self.deviceConfig = deviceConfig
        self.url = secrets.get("statusURL", DEFAULT_STATUS_URL).strip()
        self.apiKey = secrets["apiKey"]
        self.state = loadSyncState(log)

        # Backlog sync bookkeeping, set by start().
        self.syncId = None
        self.pending = []  # [(captureDateTime, bytes)] oldest first
        self.sent = 0
        self.lastProgressSent = 0
        self.lastProgressTime = 0.0

        if not self.url:
            log.debug("statusURL is blank; device status reporting is disabled.")

    def realtime(self):
        """The live capture uploaded and there is no backlog."""
        self._countSynced(1)
        self.state["lastSyncAt"] = _utcNow()
        saveSyncState(self.state, self.log)
        self._send("realtime", includeSnapshot=True)

    def start(self, pending):
        """A backlog sync is about to begin. pending is [(captureDateTime, bytes)]."""
        self._countSynced(1)  # the live capture that triggered this sync
        self.syncId = _utcNow()
        self.pending = pending
        self.sent = 0
        self.lastProgressSent = 0
        self.lastProgressTime = time.monotonic()
        self._send("start", includeSnapshot=True)

    def recordSent(self):
        """One backlog record uploaded; sends in_progress when due."""
        self.sent += 1
        due = (
            self.sent - self.lastProgressSent >= PROGRESS_EVERY_RECORDS
            or time.monotonic() - self.lastProgressTime >= PROGRESS_EVERY_SECONDS
        )
        if due and self.sent < len(self.pending):
            self.lastProgressSent = self.sent
            self.lastProgressTime = time.monotonic()
            self._send("in_progress")

    def finished(self, complete):
        self._countSynced(self.sent)
        self.state["lastSyncAt"] = _utcNow()
        saveSyncState(self.state, self.log)
        self._send(
            "finished",
            includeSnapshot=True,
            result="complete" if complete else "interrupted",
        )

    def _countSynced(self, n):
        self.state["lifetimeSynced"] = self.state.get("lifetimeSynced", 0) + n

    def _backlog(self):
        remaining = self.pending[self.sent:]
        return _dropNone({
            "pendingRecords": len(remaining),
            "pendingBytes": sum(size for _, size in remaining),
            "oldestPending": remaining[0][0] if remaining else None,
            "newestPending": remaining[-1][0] if remaining else None,
            "sentThisSync": self.sent if self.syncId else None,
            "lifetimeSynced": self.state.get("lifetimeSynced", 0),
        })

    def _send(self, syncStatus, includeSnapshot=False, result=None):
        if not self.url:
            return

        body = _dropNone({
            "deviceCode": self.deviceCode,
            "syncStatus": syncStatus,
            "syncId": self.syncId,
            "result": result,
            "deviceTime": _utcNow(),
            "backlog": self._backlog(),
        })
        # The capture snapshot and health only change once per cycle, so they
        # ride on realtime/start/finished and are left off in_progress.
        if includeSnapshot:
            body["lastCapture"] = self.lastCapture
            if self.deviceConfig:
                body["config"] = self.deviceConfig
            body["health"] = collectHealth()

        try:
            response = self.session.post(
                self.url,
                json=body,
                headers={'x-api-key': self.apiKey},
                timeout=STATUS_TIMEOUT_SECONDS,
            )
            if response.status_code not in (200, 201, 204):
                self.log.warning(
                    f"Device status '{syncStatus}' rejected: {response.status_code} - {response.text}"
                )
                return
            self.log.info(f"Device status '{syncStatus}' sent.")
            self._handleResponse(response)
        except requests.RequestException as e:
            self.log.warning(f"Device status '{syncStatus}' failed to send: {e}")

    def _handleResponse(self, response):
        # Placeholder for server -> device commands (config changes, software
        # updates, verbose diagnostics). The server may return
        # {"commands": [...]}; until command handling is built they are only
        # logged, and no commandResults are sent back.
        try:
            data = response.json()
        except ValueError:
            return
        commands = data.get("commands") if isinstance(data, dict) else None
        if commands:
            self.log.info(
                f"Server sent {len(commands)} command(s); command handling is not implemented yet, ignoring."
            )
