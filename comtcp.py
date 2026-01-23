import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import socket
import serial
import serial.tools.list_ports
import json
import time

class DualModeListenerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial & TCP Listener")

        self.mode = tk.StringVar(value="serial")
        self.serial_conn = None
        self.server_socket = None
        self.client_threads = []
        self.stop_event = threading.Event()

        self.build_gui()

    def build_gui(self):
        mode_frame = ttk.Frame(self.root)
        mode_frame.pack(pady=5)

        ttk.Radiobutton(mode_frame, text="Serial", variable=self.mode, value="serial", command=self.update_mode).pack(side="left")
        ttk.Radiobutton(mode_frame, text="TCP/IP", variable=self.mode, value="tcp", command=self.update_mode).pack(side="left")

        self.config_frame = ttk.Frame(self.root)
        self.config_frame.pack(pady=5)

        # Serial config
        self.serial_frame = ttk.Frame(self.config_frame)
        self.serial_port_var = tk.StringVar()
        self.baud_rate_var = tk.StringVar(value="9600")

        ttk.Label(self.serial_frame, text="Port:").pack(side="left")
        self.serial_ports = ttk.Combobox(self.serial_frame, textvariable=self.serial_port_var, width=10)
        self.serial_ports.pack(side="left")
        self.refresh_ports()

        ttk.Label(self.serial_frame, text="Baud:").pack(side="left")
        ttk.Entry(self.serial_frame, textvariable=self.baud_rate_var, width=8).pack(side="left")

        ttk.Button(self.serial_frame, text="Refresh Ports", command=self.refresh_ports).pack(side="left")

        # TCP config
        self.tcp_frame = ttk.Frame(self.config_frame)
        self.ip_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.StringVar(value="9000")

        ttk.Label(self.tcp_frame, text="IP:").pack(side="left")
        ttk.Entry(self.tcp_frame, textvariable=self.ip_var, width=15).pack(side="left")
        ttk.Label(self.tcp_frame, text="Port:").pack(side="left")
        ttk.Entry(self.tcp_frame, textvariable=self.port_var, width=6).pack(side="left")

        self.serial_frame.pack()

        # Control buttons
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=5)
        ttk.Button(control_frame, text="Start", command=self.start_listening).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Stop", command=self.stop_listening).pack(side="left", padx=5)

        # Text areas
        self.received_text = self.create_text_area("Received Data")
        self.sent_text = self.create_text_area("Sent Data")

    def create_text_area(self, title):
        frame = ttk.LabelFrame(self.root, text=title)
        frame.pack(fill="both", expand=True, padx=10, pady=5)
        text = scrolledtext.ScrolledText(frame, wrap="word", height=10)
        text.pack(fill="both", expand=True)
        return text

    def update_mode(self):
        if self.mode.get() == "serial":
            self.tcp_frame.pack_forget()
            self.serial_frame.pack()
        else:
            self.serial_frame.pack_forget()
            self.tcp_frame.pack()

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.serial_ports["values"] = ports
        if ports:
            self.serial_ports.current(0)

    def start_listening(self):
        self.stop_event.clear()
        if self.mode.get() == "serial":
            self.listen_serial()
        else:
            self.listen_tcp()

    def stop_listening(self):
        self.stop_event.set()
        if self.serial_conn:
            self.serial_conn.close()
        if self.server_socket:
            self.server_socket.close()
        for t in self.client_threads:
            t.join()

    def listen_serial(self):
        try:
            self.serial_conn = serial.Serial(self.serial_port_var.get(), int(self.baud_rate_var.get()), timeout=1)
            threading.Thread(target=self.serial_reader, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Serial Error", str(e))

    def serial_reader(self):
        while not self.stop_event.is_set():
            try:
                line = self.serial_conn.readline().decode(errors='ignore').strip()
                if line:
                    self.handle_data(line)
            except Exception as e:
                print("Serial read error:", e)

    def listen_tcp(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((self.ip_var.get(), int(self.port_var.get())))
            self.server_socket.listen(5)
            threading.Thread(target=self.tcp_accept_loop, daemon=True).start()
        except Exception as e:
            messagebox.showerror("TCP Error", str(e))

    def tcp_accept_loop(self):
        while not self.stop_event.is_set():
            try:
                client_sock, addr = self.server_socket.accept()
                self.log_received(f"[TCP] Connection from {addr}")
                t = threading.Thread(target=self.handle_client, args=(client_sock,), daemon=True)
                self.client_threads.append(t)
                t.start()
            except:
                break

    def handle_client(self, sock):
        with sock:
            while not self.stop_event.is_set():
                try:
                    data = sock.recv(4096)
                    if not data:
                        break
                    text = data.decode(errors='ignore').strip()
                    self.handle_data(text)
                except:
                    break

    def handle_data(self, text):
        self.log_received(text)
        json_data = json.dumps({"data": text})
        self.log_sent(json_data)

    def log_received(self, msg):
        self.received_text.insert("end", msg + "\n")
        self.received_text.see("end")

    def log_sent(self, msg):
        self.sent_text.insert("end", msg + "\n")
        self.sent_text.see("end")

if __name__ == "__main__":
    root = tk.Tk()
    app = DualModeListenerApp(root)
    root.mainloop()
