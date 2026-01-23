import tkinter as tk
from tkinter import messagebox, scrolledtext
import socket
import threading
import json
import os
from datetime import datetime
import requests

CONFIG_FILE = "settings.json"
DEFAULT_API_URL = "http://localhost:8000/api/receive"

server_socket = None
is_listening = False
client_threads = []
connected_clients = []

# === Utility Functions ===
def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_event(text):
    event_log.insert(tk.END, text + "\n")
    event_log.see(tk.END)

def update_connection_list():
    client_listbox.delete(0, tk.END)
    for addr in connected_clients:
        client_listbox.insert(tk.END, f"{addr[0]}:{addr[1]}")

# === Networking Functions ===
def start_server(ip, port, api_url):
    global server_socket, is_listening

    if is_listening:
        log_event("Server already running.")
        return

    def client_handler(client_socket, addr):
        connected_clients.append(addr)
        update_connection_list()
        try:
            data = client_socket.recv(4096).decode("utf-8")
            try:
                parsed = json.loads(data)
                formatted = json.dumps(parsed, indent=2)
                log_event(f"[{timestamp()}] JSON from {addr}:\n{formatted}")
            except json.JSONDecodeError:
                log_event(f"[{timestamp()}] Text from {addr}: {data}")

            # Send to API
            try:
                response = requests.post(api_url, data=data, timeout=5)
                log_event(f"[{timestamp()}] Forwarded to API: {response.status_code} {response.text}")
            except Exception as e:
                log_event(f"[{timestamp()}] API Forwarding Error: {e}")

        except Exception as e:
            log_event(f"[{timestamp()}] Error from {addr}: {e}")
        finally:
            client_socket.close()
            connected_clients.remove(addr)
            update_connection_list()

    def run():
        global is_listening
        is_listening = True

        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((ip, port))
            server_socket.listen(10)
            log_event(f"[{timestamp()}] Listening on {ip}:{port}")

            while is_listening:
                try:
                    client_socket, addr = server_socket.accept()
                    thread = threading.Thread(target=client_handler, args=(client_socket, addr), daemon=True)
                    client_threads.append(thread)
                    thread.start()
                except Exception as e:
                    log_event(f"[{timestamp()}] Server error: {e}")
        except Exception as e:
            log_event(f"[{timestamp()}] Failed to start server: {e}")
            is_listening = False

    threading.Thread(target=run, daemon=True).start()

# === GUI Functions ===
def save_settings():
    ip = ip_entry.get().strip()
    port = port_entry.get().strip()
    api = api_entry.get().strip() or DEFAULT_API_URL

    if not ip or not port:
        messagebox.showwarning("Missing Data", "Please enter both IP and port.")
        return

    try:
        port = int(port)
    except ValueError:
        messagebox.showerror("Invalid Port", "Port must be a number.")
        return

    with open(CONFIG_FILE, "w") as f:
        json.dump({"ip_address": ip, "port": port, "api_url": api}, f)

    update_listening_label()
    start_server(ip, port, api)

def update_listening_label():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            listening_text.set(f"{data['ip_address']}:{data['port']}")
    else:
        listening_text.set("None")

# === GUI Setup ===
root = tk.Tk()
root.title("LIS")
root.geometry("700x600")

# Frame 1 – Config
frame1 = tk.LabelFrame(root, text="1. Configure Listener", padx=10, pady=10)
frame1.pack(fill="x", padx=10, pady=5)

tk.Label(frame1, text="IP Address:").grid(row=0, column=0, sticky="e")
ip_entry = tk.Entry(frame1, width=20)
ip_entry.grid(row=0, column=1, padx=5)

tk.Label(frame1, text="Port:").grid(row=0, column=2, sticky="e")
port_entry = tk.Entry(frame1, width=10)
port_entry.grid(row=0, column=3, padx=5)

tk.Label(frame1, text="API URL:").grid(row=0, column=4, sticky="e")
api_entry = tk.Entry(frame1, width=30)
api_entry.grid(row=0, column=5, padx=5)

tk.Button(frame1, text="Start Listening", command=save_settings, bg="#4CAF50", fg="white").grid(row=0, column=6, padx=10)

# Frame 2 – Listener Status
frame2 = tk.LabelFrame(root, text="2. Listener Status", padx=10, pady=10)
frame2.pack(fill="x", padx=10, pady=5)

listening_text = tk.StringVar(value="None")
tk.Label(frame2, text="Currently Listening On:", font=("Arial", 10, "bold")).pack(side="left")
tk.Label(frame2, textvariable=listening_text, fg="blue", font=("Arial", 10)).pack(side="left", padx=10)

# Frame 3 – Event Log
frame3 = tk.LabelFrame(root, text="3. Event Log", padx=10, pady=10)
frame3.pack(fill="both", expand=True, padx=10, pady=5)

event_log = scrolledtext.ScrolledText(frame3, height=15, wrap="word", font=("Courier", 10))
event_log.pack(fill="both", expand=True)

# Frame 4 – Connected Clients
frame4 = tk.LabelFrame(root, text="4. Active Connections", padx=10, pady=10)
frame4.pack(fill="both", expand=True, padx=10, pady=5)

client_listbox = tk.Listbox(frame4, font=("Arial", 10))
client_listbox.pack(fill="both", expand=True)

# Load config if exists
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
        ip_entry.insert(0, config.get("ip_address", ""))
        port_entry.insert(0, str(config.get("port", "")))
        api_entry.insert(0, config.get("api_url", ""))
        update_listening_label()
        start_server(config["ip_address"], config["port"], config.get("api_url", DEFAULT_API_URL))

root.mainloop()
