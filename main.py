import tkinter as tk
from tkinter import messagebox, scrolledtext
import json
import os
import socket
import threading
from datetime import datetime
import requests

CONFIG_FILE = "settings.json"
server_socket = None
server_thread = None
is_listening = False

auth_token = ""

API_URL = "http://127.0.0.1:8003/api/hl7/receive"


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_event(msg):
    event_log.insert(tk.END, f"[{timestamp()}] {msg}\n")
    event_log.see(tk.END)

def log_sent(msg):
    sent_log.insert(tk.END, f"[{timestamp()}] {msg}\n")
    sent_log.see(tk.END)

# --- Server Logic ---
def start_server(ip, port):
    global server_socket, is_listening

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((ip, int(port)))
        server_socket.listen(10)
        is_listening = True
        log_event(f"Server listening on {ip}:{port}")
    except Exception as e:
        log_event(f"Socket error: {e}")
        return

    while is_listening:
        try:
            client_socket, address = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_socket, address), daemon=True)
            client_thread.start()
        except Exception as e:
            log_event(f"Accept error: {e}")
            break
def update_listening_frame():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            listening_text.set(f"{data['ip_address']}:{data['port']}")
    else:
        listening_text.set("None")

def simulate_event():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            ip, port = data["ip_address"], data["port"]
            log = f"[{timestamp()}] Event received at {ip}:{port}\n"
            event_log.insert(tk.END, log)
            event_log.see(tk.END)
    else:
        messagebox.showerror("No Listener", "Please set an IP and port first.")

def handle_client(client_socket, address):
    try:
        data = client_socket.recv(4096).decode('utf-8')
        client_socket.close()

        if not data.strip():
            return

        try:
            parsed = json.loads(data)
            pretty_json = json.dumps(parsed, indent=2)
            log_event(f"JSON from {address}:\n{pretty_json}")
            send_to_api(parsed)
        except json.JSONDecodeError:
            log_event(f"Invalid JSON from {address}: {data.strip()}")

    except Exception as e:
        log_event(f"Error handling client {address}: {e}")

def send_to_api(data):
    # Fetch CSRF token first
    csrf_response = requests.get("http://127.0.0.1:8003/csrf-token")
    csrf_token = csrf_response.json().get("csrf_token")

    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
        "X-CSRF-TOKEN": csrf_token  # Add CSRF token in header
    }

    # Send POST request with CSRF token
    try:
        response = requests.post(API_URL, json=data, headers=headers, timeout=5)
        if response.status_code == 200:
            log_sent(f"Sent to API: Success ({response.status_code})")
        else:
            log_sent(f"API Error {response.status_code}: {response.text}")
    except Exception as e:
        log_sent(f"Failed to send to API: {e}")

def stop_server():
    global is_listening, server_socket
    is_listening = False
    if server_socket:
        try:
            server_socket.close()
        except:
            pass
        server_socket = None

# --- GUI Logic ---
def save_data():
    ip = ip_entry.get().strip()
    port = port_entry.get().strip()
    token = token_entry.get().strip()

    if not ip or not port:
        messagebox.showwarning("Input Required", "Please enter IP address and port.")
        return

    try:
        int(port)
    except ValueError:
        messagebox.showerror("Invalid Port", "Port must be a number.")
        return

    with open(CONFIG_FILE, "w") as f:
        json.dump({"ip_address": ip, "port": port, "token": token}, f)

    update_listening_frame()
    start_listening(ip, port)

def start_listening(ip, port):
    global server_thread, auth_token
    auth_token = token_entry.get().strip()
    stop_server()
    server_thread = threading.Thread(target=start_server, args=(ip, port), daemon=True)
    server_thread.start()


def start_listening(ip, port):
    global server_thread
    stop_server()  # Stop any existing server
    server_thread = threading.Thread(target=start_server, args=(ip, port), daemon=True)
    server_thread.start()

def on_close():
    stop_server()
    root.destroy()

# === GUI Setup ===
root = tk.Tk()
root.title("TS LIS SERVER")
root.geometry("750x650")
root.resizable(False, False)
root.protocol("WM_DELETE_WINDOW", on_close)

# Frame 1 – Save IP, Port, Token
frame1 = tk.LabelFrame(root, text="1. Save IP, Port & Token", padx=10, pady=10)
frame1.pack(fill="x", padx=10, pady=5)

tk.Label(frame1, text="IP Address:").grid(row=0, column=0, padx=5, pady=5)
ip_entry = tk.Entry(frame1, width=20)
ip_entry.grid(row=0, column=1, padx=5)

tk.Label(frame1, text="Port:").grid(row=0, column=2, padx=5)
port_entry = tk.Entry(frame1, width=10)
port_entry.grid(row=0, column=3, padx=5)

tk.Label(frame1, text="Token:").grid(row=1, column=0, padx=5, pady=5)
token_entry = tk.Entry(frame1, width=45, show="*")
token_entry.grid(row=1, column=1, columnspan=3, padx=5)

tk.Button(frame1, text="Save", command=save_data, bg="#4CAF50", fg="white").grid(row=1, column=4, padx=10)

# Frame 2 – Show Listening IPs
frame2 = tk.LabelFrame(root, text="2. Current Listening Address", padx=10, pady=10)
frame2.pack(fill="x", padx=10, pady=5)

listening_text = tk.StringVar(value="None")
tk.Label(frame2, text="Currently Listening On:", font=("Arial", 10, "bold")).pack(side="left")
tk.Label(frame2, textvariable=listening_text, fg="blue", font=("Arial", 10)).pack(side="left", padx=10)

# Frame 3 – Event Log (Received Data)
frame3 = tk.LabelFrame(root, text="3. Received Data (JSON Events)", padx=10, pady=10)
frame3.pack(fill="both", expand=True, padx=10, pady=5)

event_log = scrolledtext.ScrolledText(frame3, height=10, wrap="word", font=("Courier", 10))
event_log.pack(fill="both", expand=True)

# Frame 4 – Sent Log (Forwarded to API)
frame4 = tk.LabelFrame(root, text="4. Sent Data (To API)", padx=10, pady=10)
frame4.pack(fill="both", expand=True, padx=10, pady=5)

sent_log = scrolledtext.ScrolledText(frame4, height=10, wrap="word", font=("Courier", 10))
sent_log.pack(fill="both", expand=True)

# Load previous settings and start server
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        data = json.load(f)
        ip_entry.insert(0, data.get("ip_address", ""))
        port_entry.insert(0, data.get("port", ""))
        token_entry.insert(0, data.get("token", ""))
        auth_token = data.get("token", "")
        update_listening_frame()
        start_listening(data["ip_address"], data["port"])


root.mainloop()


