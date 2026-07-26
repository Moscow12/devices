"""
Hikvision Attendance Agent
==========================

Pulls attendance events from a Hikvision DS-K1A8603EF-B fingerprint terminal
(via ISAPI over the LAN) and pushes them to a remote Laravel HR application
(via HTTPS with HMAC signing).

Designed to run on a small Windows/Linux machine inside the hospital network,
on a schedule (cron / Task Scheduler) or as a long-running service.

Architecture:
    [Hikvision device on LAN]  <--HTTP/Digest--  [this agent]  --HTTPS+HMAC-->  [Laravel HRP online]

Idempotency:
    Every event has a monotonically increasing `serialNo` per device.
    We persist the last-seen serialNo per device locally (state.json) and on
    the Laravel side we also enforce a unique (device_serial, serial_no) index.
    The puller is therefore safe to re-run.

Author: techscales Co. Ltd
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import requests
from requests.auth import HTTPDigestAuth

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# In production, load these from a .env file or Windows registry rather than
# hard-coding. Keeping them here for clarity in this reference script.

CONFIG_PATH = Path(__file__).parent / "config.json"
STATE_PATH  = Path(__file__).parent / "state.json"
LOG_PATH    = Path(__file__).parent / "agent.log"

# How far back to look on the very first run if we have no state yet.
FIRST_RUN_LOOKBACK_DAYS = 7

# Page size — the device caps this around 30 regardless of what we ask for.
PAGE_SIZE = 30

# AcsEvent major/minor codes for valid attendance authentication.
# major=5 (access control event), minor=75 ("Authentication via card/face/fp succeeded")
EVENT_MAJOR = 5

# Network timeouts (seconds)
DEVICE_TIMEOUT  = 30
LARAVEL_TIMEOUT = 20

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("hik-agent")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DeviceConfig:
    name: str            # human-readable, e.g. "Main Gate - Moshi"
    serial: str          # device serial from the back of the unit, used as stable ID
    host: str            # LAN IP, e.g. "192.168.1.50"
    port: int            # usually 80
    username: str        # device admin username
    password: str        # device admin password
    use_https: bool = False


@dataclass(frozen=True)
class LaravelConfig:
    endpoint: str        # https://hrp.your-hospital.tz/api/attendance/ingest
    hmac_secret: str     # shared secret for request signing


@dataclass
class AttendanceEvent:
    """Normalized event we send to Laravel."""
    device_serial: str
    serial_no: int               # device-side unique sequence
    employee_no: str             # staff number programmed on the device
    event_time: str              # ISO 8601 with timezone
    attendance_status: str       # checkIn | checkOut | breakIn | breakOut | overtimeIn | overtimeOut | undefined
    verify_mode: str             # e.g. "fingerprint", "card", "fingerOrFace"
    door_no: int | None
    raw: dict                    # full original payload for audit


# ---------------------------------------------------------------------------
# Config / state persistence
# ---------------------------------------------------------------------------
def load_config() -> tuple[list[DeviceConfig], LaravelConfig]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Missing {CONFIG_PATH}. Copy config.example.json to config.json and edit it."
        )
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    devices = [DeviceConfig(**d) for d in raw["devices"]]
    laravel = LaravelConfig(**raw["laravel"])
    return devices, laravel


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    with STATE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    # Atomic write to avoid corrupting state if the process is killed mid-write.
    tmp = STATE_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    tmp.replace(STATE_PATH)


# ---------------------------------------------------------------------------
# Hikvision ISAPI client
# ---------------------------------------------------------------------------
class HikvisionClient:
    """Thin wrapper around the AcsEvent ISAPI endpoint."""

    def __init__(self, device: DeviceConfig):
        self.device = device
        scheme = "https" if device.use_https else "http"
        self.base_url = f"{scheme}://{device.host}:{device.port}"
        self.auth = HTTPDigestAuth(device.username, device.password)
        self.session = requests.Session()
        # Most Hikvision devices ship with self-signed certs that fail validation.
        # If you enable HTTPS in production, install the device cert into the trust
        # store rather than disabling verification.
        self.session.verify = False if device.use_https else True

    def fetch_events_page(
        self,
        start: datetime,
        end: datetime,
        position: int,
    ) -> dict:
        """One page of AcsEvent results."""
        url = f"{self.base_url}/ISAPI/AccessControl/AcsEvent?format=json"
        body = {
            "AcsEventCond": {
                "searchID": str(uuid.uuid4()),
                "searchResultPosition": position,
                "maxResults": PAGE_SIZE,
                "major": EVENT_MAJOR,
                "minor": 0,                 # 0 = all minor types under this major
                "startTime": start.isoformat(timespec="seconds"),
                "endTime":   end.isoformat(timespec="seconds"),
                # Filter to valid authentication only — drops noise like
                # "currentVerifyMode: invalid" failed-auth events.
                "eventAttribute": "attendance",
            }
        }
        log.debug("POST %s body=%s", url, body)
        resp = self.session.post(
            url,
            json=body,
            auth=self.auth,
            timeout=DEVICE_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def iter_events(
        self,
        start: datetime,
        end: datetime,
    ) -> Iterator[dict]:
        """Yield every InfoList entry between start and end, paginating until OK."""
        position = 0
        while True:
            page = self.fetch_events_page(start, end, position)
            payload = page.get("AcsEvent", {})
            info_list = payload.get("InfoList", []) or []
            log.info(
                "Device %s: page position=%d returned=%d total=%d status=%s",
                self.device.serial,
                position,
                len(info_list),
                payload.get("totalMatches", 0),
                payload.get("responseStatusStrg"),
            )
            for entry in info_list:
                yield entry

            status = payload.get("responseStatusStrg", "OK")
            num_returned = payload.get("numOfMatches", len(info_list))

            # The device returns "MORE" while there are still pages, "OK" when done.
            if status != "MORE" or num_returned == 0:
                return
            position += num_returned


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------
def normalize(device: DeviceConfig, raw: dict) -> AttendanceEvent | None:
    """Convert one ISAPI InfoList entry to our AttendanceEvent shape.

    Returns None for entries we want to skip (e.g. events with no employee number,
    or invalid-auth events that slipped past the filter).
    """
    employee_no = raw.get("employeeNoString") or raw.get("employeeNo")
    if not employee_no:
        return None

    verify_mode = raw.get("currentVerifyMode") or ""
    if verify_mode == "invalid":
        return None

    serial_no = raw.get("serialNo")
    if serial_no is None:
        return None

    return AttendanceEvent(
        device_serial    = device.serial,
        serial_no        = int(serial_no),
        employee_no      = str(employee_no),
        event_time       = raw["time"],
        attendance_status= raw.get("attendanceStatus") or "undefined",
        verify_mode      = verify_mode,
        door_no          = raw.get("doorNo"),
        raw              = raw,
    )


# ---------------------------------------------------------------------------
# Laravel push (HMAC-signed)
# ---------------------------------------------------------------------------
def push_to_laravel(
    cfg: LaravelConfig,
    events: list[AttendanceEvent],
) -> int:
    """Send a batch to the HRP. Returns the number of events Laravel accepted.

    Signing scheme:
        timestamp = current unix seconds
        body      = canonical JSON of the request
        signature = HMAC-SHA256(secret, f"{timestamp}.{body}")

        Headers:
            X-Agent-Timestamp: <timestamp>
            X-Agent-Signature: <hex signature>

    The Laravel side verifies the signature and that `abs(now - timestamp) < 300`.
    """
    if not events:
        return 0

    payload = {
        "events": [
            {
                "device_serial":     e.device_serial,
                "serial_no":         e.serial_no,
                "employee_no":       e.employee_no,
                "event_time":        e.event_time,
                "attendance_status": e.attendance_status,
                "verify_mode":       e.verify_mode,
                "door_no":           e.door_no,
            }
            for e in events
        ]
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    timestamp = str(int(time.time()))
    signature = hmac.new(
        cfg.hmac_secret.encode("utf-8"),
        f"{timestamp}.{body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type":      "application/json",
        "X-Agent-Timestamp": timestamp,
        "X-Agent-Signature": signature,
    }

    resp = requests.post(
        cfg.endpoint,
        data=body,
        headers=headers,
        timeout=LARAVEL_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    accepted = data.get("accepted", 0)
    log.info(
        "Laravel accepted %d / %d events (duplicates skipped: %d)",
        accepted,
        len(events),
        data.get("duplicates", 0),
    )
    return accepted


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def process_device(
    device: DeviceConfig,
    laravel: LaravelConfig,
    state: dict,
) -> None:
    log.info("=== Device: %s (%s @ %s) ===", device.name, device.serial, device.host)

    # Determine the time window. Devices need both startTime and endTime; we use
    # the time window approach (rather than serialNo cursoring) because it's the
    # only filter the device firmware reliably honors.
    now = datetime.now(timezone.utc).astimezone()  # local tz with offset
    device_state = state.setdefault(device.serial, {})
    last_seen_serial = device_state.get("last_serial_no", 0)
    last_run_iso = device_state.get("last_run")

    if last_run_iso:
        # Look back a small overlap (1 hour) to catch any events the device
        # hadn't yet flushed at the previous run boundary. Idempotency on
        # (device_serial, serial_no) makes the overlap safe.
        start = datetime.fromisoformat(last_run_iso) - timedelta(hours=1)
    else:
        start = now - timedelta(days=FIRST_RUN_LOOKBACK_DAYS)
        log.info("First run: looking back %d days", FIRST_RUN_LOOKBACK_DAYS)

    end = now

    client = HikvisionClient(device)
    new_events: list[AttendanceEvent] = []
    max_serial_seen = last_seen_serial

    try:
        for raw in client.iter_events(start, end):
            evt = normalize(device, raw)
            if evt is None:
                continue
            # Skip serials we've already pushed (defensive — Laravel also dedupes).
            if evt.serial_no <= last_seen_serial:
                continue
            new_events.append(evt)
            if evt.serial_no > max_serial_seen:
                max_serial_seen = evt.serial_no
    except requests.RequestException as e:
        log.error("Failed to read from device %s: %s", device.serial, e)
        return

    log.info("Device %s: %d new events to push", device.serial, len(new_events))

    if not new_events:
        device_state["last_run"] = end.isoformat()
        save_state(state)
        return

    # Push in batches of 100 to keep request bodies reasonable.
    BATCH = 100
    pushed_total = 0
    for i in range(0, len(new_events), BATCH):
        batch = new_events[i : i + BATCH]
        try:
            pushed_total += push_to_laravel(laravel, batch)
        except requests.RequestException as e:
            log.error("Failed to push batch to Laravel: %s", e)
            # Stop on first failure so we don't advance the cursor past
            # events Laravel never received.
            save_state(state)
            return

    device_state["last_serial_no"] = max_serial_seen
    device_state["last_run"]       = end.isoformat()
    save_state(state)
    log.info(
        "Device %s done: pushed=%d new last_serial_no=%d",
        device.serial,
        pushed_total,
        max_serial_seen,
    )


def main() -> int:
    try:
        devices, laravel = load_config()
    except Exception as e:
        log.error("Config error: %s", e)
        return 2

    state = load_state()

    for device in devices:
        try:
            process_device(device, laravel, state)
        except Exception as e:
            # One device blowing up shouldn't stop the others.
            log.exception("Unhandled error for device %s: %s", device.serial, e)

    return 0


if __name__ == "__main__":
    # Suppress urllib3 warning when use_https=True with self-signed certs.
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    sys.exit(main())
