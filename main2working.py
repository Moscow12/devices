import tkinter as tk
from tkinter import messagebox, scrolledtext
import json
import os
import socket
import threading
from datetime import datetime

CONFIG_FILE = "settings.json"
server_socket = None
server_thread = None
is_listening = False

def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_event(msg):
    event_log.insert(tk.END, f"[{timestamp()}] {msg}\n")
    event_log.see(tk.END)

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
        except json.JSONDecodeError:
            log_event(f"Invalid JSON from {address}: {data.strip()}")

    except Exception as e:
        log_event(f"Error handling client {address}: {e}")

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

    if not ip or not port:
        messagebox.showwarning("Input Required", "Please enter both IP address and port.")
        return

    try:
        int(port)
    except ValueError:
        messagebox.showerror("Invalid Port", "Port must be a number.")
        return

    with open(CONFIG_FILE, "w") as f:
        json.dump({"ip_address": ip, "port": port}, f)

    update_listening_frame()
    start_listening(ip, port)

def update_listening_frame():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            listening_text.set(f"{data['ip_address']}:{data['port']}")
    else:
        listening_text.set("None")

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
root.geometry("700x550")
root.resizable(False, False)
root.protocol("WM_DELETE_WINDOW", on_close)

# Frame 1 – Save IP and Port
frame1 = tk.LabelFrame(root, text="1. Save IP and Port", padx=10, pady=10)
frame1.pack(fill="x", padx=10, pady=5)

tk.Label(frame1, text="IP Address:").grid(row=0, column=0, padx=5, pady=5)
ip_entry = tk.Entry(frame1, width=25)
ip_entry.grid(row=0, column=1, padx=5)

tk.Label(frame1, text="Port:").grid(row=0, column=2, padx=5, pady=5)
port_entry = tk.Entry(frame1, width=10)
port_entry.grid(row=0, column=3, padx=5)

tk.Button(frame1, text="Save", command=save_data, bg="#4CAF50", fg="white").grid(row=0, column=4, padx=10)

# Frame 2 – Show Listening IPs
frame2 = tk.LabelFrame(root, text="2. Current Listening Address", padx=10, pady=10)
frame2.pack(fill="x", padx=10, pady=5)

listening_text = tk.StringVar(value="None")
tk.Label(frame2, text="Currently Listening On:", font=("Arial", 10, "bold")).pack(side="left")
tk.Label(frame2, textvariable=listening_text, fg="blue", font=("Arial", 10)).pack(side="left", padx=10)

# Frame 3 – Event Log
frame3 = tk.LabelFrame(root, text="3. Event Log (JSON + Multiple Clients)", padx=10, pady=10)
frame3.pack(fill="both", expand=True, padx=10, pady=5)

event_log = scrolledtext.ScrolledText(frame3, height=20, wrap="word", font=("Courier", 10))
event_log.pack(fill="both", expand=True)

# Load previous settings and start server
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        data = json.load(f)
        ip_entry.insert(0, data.get("ip_address", ""))
        port_entry.insert(0, data.get("port", ""))
        update_listening_frame()
        start_listening(data["ip_address"], data["port"])

root.mainloop()
