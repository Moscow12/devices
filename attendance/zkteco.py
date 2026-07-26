import os
import time
import logging
from datetime import datetime
from zk import ZK, const
from zk.exception import ZKErrorResponse
import requests

# ===================== CONFIG =====================
DEVICE_IP = "192.168.0.201"
DEVICE_PORT = 4370

# Device authentication.
#
# IMPORTANT: The ZKTeco protocol authenticates ONLY with the device's COMM Key
# (Menu -> Comm -> Security -> COMM Key). It is the ONLY value that prevents an
# "Unauthenticated" error. It must be set in DEVICE_PASSWORD.
#   - If the device's COMM Key is 0 (default), set DEVICE_PASSWORD = 0.
#     Sending a non-zero password when the key is 0 also causes "Unauthenticated".
#   - If the device's COMM Key is e.g. 123456, set DEVICE_PASSWORD = 123456.
#
# DEVICE_ID is NOT used for authentication. It is the device's number (a label)
# used only to tag synced logs. It does nothing for the connection.
DEVICE_ID = os.environ.get("ZK_DEVICE_ID", "100")
DEVICE_PASSWORD = int(os.environ.get("ZK_DEVICE_PASSWORD", "0"))

LARAVEL_API_URL = "https://his-test.cssc.or.tz/api/attendance/receive"
LAST_SYNC_FILE = "last_sync.txt"
DEVICE_CONFIG_FILE = "device.txt"
LOG_FILE = "sync.log"
SYNC_INTERVAL = 300  # 1 hour in seconds
# ===================================================

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def load_device_config():
    """Loads stored device ID and password from DEVICE_CONFIG_FILE if present.

    Falls back to the CONFIG / environment values. The file is a simple
    key=value format:
        id=<device id>
        password=<comm key integer>
    """
    device_id = DEVICE_ID
    password = DEVICE_PASSWORD

    if os.path.exists(DEVICE_CONFIG_FILE):
        with open(DEVICE_CONFIG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip().lower()
                value = value.strip()
                if key == "id":
                    device_id = value
                elif key == "password":
                    try:
                        password = int(value)
                    except ValueError:
                        logging.warning(
                            f"Invalid password in {DEVICE_CONFIG_FILE}; using default."
                        )

    return device_id, password


def save_device_config(device_id, password):
    """Persists the device ID and password so they are recorded for reuse."""
    with open(DEVICE_CONFIG_FILE, "w") as f:
        f.write(f"id={device_id}\n")
        f.write(f"password={password}\n")
    logging.info(f"Recorded device credentials to {DEVICE_CONFIG_FILE} (id={device_id}).")


def get_last_sync_time():
    """Reads last sync time from file or creates it with a default old date."""
    if not os.path.exists(LAST_SYNC_FILE):
        logging.warning("last_sync.txt not found. Creating with default old date.")
        with open(LAST_SYNC_FILE, "w") as f:
            f.write("2026-06-01 00:00:00")
        return datetime(2026, 1, 1, 0, 0, 0)

    with open(LAST_SYNC_FILE, "r") as f:
        return datetime.strptime(f.read().strip(), "%Y-%m-%d %H:%M:%S")

def update_last_sync_time(dt):
    """Updates last sync time in file."""
    with open(LAST_SYNC_FILE, "w") as f:
        f.write(dt.strftime("%Y-%m-%d %H:%M:%S"))

def sync_attendance():
    """Connects to ZKTeco device, fetches new logs, sends to Laravel API."""
    conn = None
    device_id, password = DEVICE_ID, DEVICE_PASSWORD
    try:
        logging.info("Starting attendance sync...")

        device_id, password = load_device_config()
        logging.info(
            f"Attempting to connect to device "
            f"(id={device_id or 'N/A'}) at {DEVICE_IP}:{DEVICE_PORT} "
            f"using {'a password' if password else 'no password'}."
        )

        zk = ZK(
            DEVICE_IP,
            port=DEVICE_PORT,
            timeout=50,
            password=password,
            force_udp=False,
            ommit_ping=False,
        )

        conn = zk.connect()

        # Connection succeeded — record the credentials that worked and report device info.
        save_device_config(device_id, password)
        try:
            serial = conn.get_serialnumber()
            logging.info(
                f"Successfully connected to device (id={device_id or 'N/A'}, "
                f"serial={serial}) at {DEVICE_IP}:{DEVICE_PORT}."
            )
        except Exception:
            logging.info(
                f"Successfully connected to device (id={device_id or 'N/A'}) "
                f"at {DEVICE_IP}:{DEVICE_PORT}."
            )

        last_sync = get_last_sync_time()

        new_logs = []
        for att in conn.get_attendance():
            att_time = att.timestamp
            if att_time > last_sync:
                new_logs.append({
                    "user_id": att.user_id,
                    "timestamp": att_time.strftime("%Y-%m-%d %H:%M:%S"),
                })

        if not new_logs:
            logging.info("No new attendance logs found.")
            return

        logging.info(f"Found {len(new_logs)} new logs. Sending to Laravel...")

        response = requests.post(LARAVEL_API_URL, json=new_logs)
        if response.status_code == 200:
            logging.info("Logs synced successfully.")
            latest_time = max(datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S") for log in new_logs)
            update_last_sync_time(latest_time)
        else:
            logging.error(f"Failed to sync logs. Status: {response.status_code}, Response: {response.text}")

    except ZKErrorResponse as e:
        if "unauthenticated" in str(e).lower():
            logging.error(
                f"Device {DEVICE_IP}:{DEVICE_PORT} rejected the connection as "
                f"Unauthenticated. The COMM Key (password={password}) does not "
                f"match the device. Check Menu -> Comm -> Security -> COMM Key on "
                f"the device and set DEVICE_PASSWORD to exactly that value "
                f"(use 0 if the COMM Key is 0). NOTE: the device ID ({device_id}) "
                f"is NOT used for authentication."
            )
        else:
            logging.exception(
                f"Device {DEVICE_IP}:{DEVICE_PORT} returned an error: {str(e)}"
            )
    except Exception as e:
        logging.exception(f"Failed to connect/sync with device {DEVICE_IP}:{DEVICE_PORT}: {str(e)}")
    finally:
        if conn is not None:
            try:
                conn.disconnect()
                logging.info("Disconnected from device.")
            except Exception:
                pass

if __name__ == "__main__":
    while True:
        sync_attendance()
        logging.info(f"Next sync in {SYNC_INTERVAL/60} minutes...")
        time.sleep(SYNC_INTERVAL)
