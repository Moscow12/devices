import os
import time
import logging
from datetime import datetime
from zk import ZK, const
import requests

# ===================== CONFIG =====================
DEVICE_IP = "172.16.1.207"
DEVICE_PORT = 4370
LARAVEL_API_URL = "https://hrp.stjosephhospitalmoshi.or.tz/api/attendance/receive"
LAST_SYNC_FILE = "last_sync.txt"
LOG_FILE = "sync.log"
SYNC_INTERVAL = 300  # 1 hour in seconds
# ===================================================

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

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
    try:
        logging.info("Starting attendance sync...")
        logging.info(f"Attempting to connect to device {DEVICE_IP}:{DEVICE_PORT}")
        zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=50, password=0, force_udp=False, ommit_ping=False)
        
        conn = zk.connect()
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
            conn.disconnect()
            return

        logging.info(f"Found {len(new_logs)} new logs. Sending to Laravel...")

        response = requests.post(LARAVEL_API_URL, json=new_logs)
        if response.status_code == 200:
            logging.info("Logs synced successfully.")
            latest_time = max(datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S") for log in new_logs)
            update_last_sync_time(latest_time)
        else:
            logging.error(f"Failed to sync logs. Status: {response.status_code}, Response: {response.text}")

        conn.disconnect()

    except Exception as e:
        logging.exception(f"Error during sync: {str(e)}")

if __name__ == "__main__":
    while True:
        sync_attendance()
        logging.info(f"Next sync in {SYNC_INTERVAL/60} minutes...")
        time.sleep(SYNC_INTERVAL)
