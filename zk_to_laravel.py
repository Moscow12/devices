from zk import ZK, const
import requests
import json
import datetime
import os

# CONFIGURATION
ZK_DEVICE_IP = '172.16.1.207'        # Replace with your device IP
ZK_PORT = 4370
LARAVEL_API_URL = 'http://10.64.11.11/webs/admin/api/receive.php'  # Replace with your Laravel API
LAST_SYNC_FILE = 'last_sync.txt'      # Local file to track last sync time

HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    # 'Authorization': 'Bearer YOUR_API_TOKEN'
}


def get_last_sync_time():
    if os.path.exists(LAST_SYNC_FILE):
        with open(LAST_SYNC_FILE, 'r') as f:
            try:
                return datetime.datetime.strptime(f.read().strip(), '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
    return datetime.datetime.min


def update_last_sync_time(timestamp):
    with open(LAST_SYNC_FILE, 'w') as f:
        f.write(timestamp.strftime('%Y-%m-%d %H:%M:%S'))


def send_to_laravel(data):
    try:
        response = requests.post(LARAVEL_API_URL, data=json.dumps(data), headers=HEADERS)
        print(f"Sent: {data['user_id']} @ {data['timestamp']} -> {response.status_code}")
    except Exception as e:
        print(f"Failed to send data: {e}")


def main():
    zk = ZK(ZK_DEVICE_IP, port=ZK_PORT, timeout=5, force_udp=False, ommit_ping=False)
    last_sync = get_last_sync_time()
    latest_time = last_sync

    try:
        conn = zk.connect()
        conn.disable_device()
        print("Connected to device")

        logs = conn.get_attendance()
        print(f"Fetched {len(logs)} logs from device")

        for log in logs:
            if log.timestamp > last_sync:
                data = {
                    'uid': log.uid,
                    'user_id': log.user_id,
                    'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': log.status,
                    'punch': log.punch,
                    'device_ip': ZK_DEVICE_IP,
                }
                send_to_laravel(data)

                if log.timestamp > latest_time:
                    latest_time = log.timestamp

        update_last_sync_time(latest_time)
        print(f"Updated last sync time: {latest_time}")

        conn.enable_device()
        conn.disconnect()
        print("Disconnected")

    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    main()

