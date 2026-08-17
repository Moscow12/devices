import os
import time
import logging
from datetime import datetime
import requests
from requests.auth import HTTPDigestAuth

# ===================== CONFIG =====================
DEVICE_IP = "198.168.100.122"
DEVICE_USER = "admin"
DEVICE_PASSWORD = "your_password"
LARAVEL_API_URL = "https://portal.stthomaskilakala.org/api/attendance/receive"
LAST_SYNC_FILE = "last_sync_hik.txt"
LOG_FILE = "sync_hik.log"
SYNC_INTERVAL = 300  # 5 minutes in seconds
SEARCH_PAGE_SIZE = 30
# ===================================================

BASE_URL = f"http://{DEVICE_IP}"
EVENT_SEARCH_URL = f"{BASE_URL}/ISAPI/AccessControl/AcsEvent?format=json"

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def get_last_sync_time():
    """Reads last sync time from file or creates it with a default old date."""
    if not os.path.exists(LAST_SYNC_FILE):
        logging.warning("last_sync_hik.txt not found. Creating with default old date.")
        with open(LAST_SYNC_FILE, "w") as f:
            f.write("2026-08-01 00:00:00")
        return datetime(2026, 1, 1, 0, 0, 0)

    with open(LAST_SYNC_FILE, "r") as f:
        return datetime.strptime(f.read().strip(), "%Y-%m-%d %H:%M:%S")


def update_last_sync_time(dt):
    """Updates last sync time in file."""
    with open(LAST_SYNC_FILE, "w") as f:
        f.write(dt.strftime("%Y-%m-%d %H:%M:%S"))


def fetch_events(auth, start_time, end_time):
    """Pages through the Hikvision ISAPI AcsEvent search and returns all matching events."""
    events = []
    search_id = f"hik-sync-{int(time.time())}"
    position = 0

    while True:
        payload = {
            "AcsEventCond": {
                "searchID": search_id,
                "searchResultPosition": position,
                "maxResults": SEARCH_PAGE_SIZE,
                "major": 5,  # 5 = fingerprint/card access events
                "minor": 0,
                "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            }
        }

        response = requests.post(EVENT_SEARCH_URL, auth=auth, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        match_info = data.get("AcsEvent", {})
        info_list = match_info.get("InfoList", [])
        events.extend(info_list)

        num_matches = match_info.get("numOfMatches", 0)
        total_matches = match_info.get("totalMatches", 0)

        position += num_matches
        if num_matches == 0 or position >= total_matches:
            break

    return events


def sync_attendance():
    """Connects to Hikvision device, fetches new access/fingerprint events, sends to Laravel API."""
    try:
        logging.info("Starting attendance sync...")
        logging.info(f"Attempting to connect to device {DEVICE_IP}")

        auth = HTTPDigestAuth(DEVICE_USER, DEVICE_PASSWORD)
        last_sync = get_last_sync_time()
        now = datetime.now()

        raw_events = fetch_events(auth, last_sync, now)

        new_logs = []
        for event in raw_events:
            time_str = event.get("time")
            if not time_str:
                continue
            try:
                att_time = datetime.strptime(time_str[:19], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                continue

            if att_time > last_sync:
                new_logs.append({
                    "user_id": event.get("employeeNoString") or event.get("cardNo") or "unknown",
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

    except Exception as e:
        logging.exception(f"Error during sync: {str(e)}")


if __name__ == "__main__":
    while True:
        sync_attendance()
        logging.info(f"Next sync in {SYNC_INTERVAL/60} minutes...")
        time.sleep(SYNC_INTERVAL)
