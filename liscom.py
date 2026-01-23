import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial
import serial.tools.list_ports
import threading
import requests
import json
import os
from datetime import datetime

class SerialApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Port Listener")
        self.serial_port = None
        self.running = False

        self.create_widgets()

    def create_widgets(self):
        config_frame = ttk.LabelFrame(self.root, text="Port Configuration")
        config_frame.grid(column=0, row=0, padx=10, pady=10, sticky="ew")

        ttk.Label(config_frame, text="Port:").grid(column=0, row=0, sticky="w")
        self.port_combobox = ttk.Combobox(config_frame, width=10, postcommand=self.refresh_ports)
        self.port_combobox.grid(column=1, row=0)

        self.refresh_button = ttk.Button(config_frame, text="🔄 Refresh", command=self.refresh_ports)
        self.refresh_button.grid(column=2, row=0)

        self.port_status = ttk.Label(config_frame, text="Detecting...", foreground="blue")
        self.port_status.grid(column=3, row=0, padx=5)

        ttk.Label(config_frame, text="Baudrate:").grid(column=4, row=0, padx=5, sticky="w")
        self.baud_entry = ttk.Entry(config_frame, width=10)
        self.baud_entry.insert(0, "9600")
        self.baud_entry.grid(column=5, row=0)

        ttk.Label(config_frame, text="API URL:").grid(column=6, row=0, padx=5, sticky="w")
        self.url_entry = ttk.Entry(config_frame, width=30)
        self.url_entry.insert(0, "http://127.0.0.1:8003/api/hl7/receive")
        self.url_entry.grid(column=7, row=0)

        self.start_button = ttk.Button(config_frame, text="Start", command=self.start_listening)
        self.start_button.grid(column=8, row=0, padx=5)
        self.stop_button = ttk.Button(config_frame, text="Stop", command=self.stop_listening, state=tk.DISABLED)
        self.stop_button.grid(column=9, row=0, padx=5)

        # Received / Sent / Response Text Areas
        self.recv_text = self.create_frame("Received Data", 1)
        self.sent_text = self.create_frame("Sent to URL", 2)
        self.response_text = self.create_frame("API Response", 3)

        # Initial port scan
        self.refresh_ports()

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combobox['values'] = ports
        if ports:
            self.port_combobox.set(ports[0])
            self.port_status.config(text=f"Detected: {ports[0]}", foreground="green")
        else:
            self.port_combobox.set('')
            self.port_status.config(text="No serial ports detected", foreground="red")

    def create_frame(self, title, row):
        frame = ttk.LabelFrame(self.root, text=title)
        frame.grid(column=0, row=row, padx=10, pady=5, sticky="nsew")
        text = scrolledtext.ScrolledText(frame, height=10, wrap=tk.WORD)
        text.pack(expand=True, fill='both')
        return text

    def start_listening(self):
        try:
            port = self.port_combobox.get()
            baud = int(self.baud_entry.get())
            self.serial_port = serial.Serial(port, baud, timeout=1)
            self.running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            threading.Thread(target=self.read_serial, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def stop_listening(self):
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def read_serial(self):
        while self.running:
            if self.serial_port.in_waiting:
                try:
                    data = self.serial_port.readline().decode(errors='ignore').strip()
                    if data:
                        self.recv_text.insert(tk.END, data + "\n")
                        self.recv_text.see(tk.END)
                        self.forward_data(data)
                except Exception as e:
                    self.recv_text.insert(tk.END, f"Error: {e}\n")

    def forward_data(self, data):
        url = self.url_entry.get()
        json_data = {"data": data}
        self.sent_text.insert(tk.END, json.dumps(json_data, indent=2) + "\n")
        self.sent_text.see(tk.END)

        # Save sent data
        self.save_json_file("sent", json_data)

        try:
            response = requests.post(url, json=json_data)
            response_json = response.json()
            self.response_text.insert(tk.END, json.dumps(response_json, indent=2) + "\n")
            self.response_text.see(tk.END)

            # Save response
            self.save_json_file("response", response_json)

        except Exception as e:
            self.response_text.insert(tk.END, f"API Error: {e}\n")

    def save_json_file(self, prefix, data):
        os.makedirs("logs", exist_ok=True)
        filename = f"logs/{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)


if __name__ == "__main__":
    root = tk.Tk()
    app = SerialApp(root)
    root.mainloop()
