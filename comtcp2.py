import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial
import serial.tools.list_ports
import socket
import threading
import json
import time

class DualModeListenerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial and TCP/IP Listener")

        self.mode = tk.StringVar(value="Serial")
        self.serial_port = None
        self.tcp_server = None
        self.client_threads = []
        self.running = False

        self.build_ui()
        self.detect_serial_ports()

    def build_ui(self):
        config_frame = ttk.LabelFrame(self.root, text="Configuration")
        config_frame.grid(column=0, row=0, padx=10, pady=10, sticky="ew")

        ttk.Label(config_frame, text="Mode:").grid(column=0, row=0, sticky="w")
        ttk.Radiobutton(config_frame, text="Serial", variable=self.mode, value="Serial", command=self.update_mode).grid(column=1, row=0, sticky="w")
        ttk.Radiobutton(config_frame, text="TCP/IP", variable=self.mode, value="TCP", command=self.update_mode).grid(column=2, row=0, sticky="w")

        self.port_label = ttk.Label(config_frame, text="Serial Port:")
        self.port_label.grid(column=0, row=1, sticky="w")
        self.port_combobox = ttk.Combobox(config_frame, width=15)
        self.port_combobox.grid(column=1, row=1, sticky="w")

        self.baud_label = ttk.Label(config_frame, text="Baudrate:")
        self.baud_label.grid(column=2, row=1, sticky="w")
        self.baud_entry = ttk.Entry(config_frame, width=10)
        self.baud_entry.insert(0, "9600")
        self.baud_entry.grid(column=3, row=1, sticky="w")

        self.ip_label = ttk.Label(config_frame, text="IP:")
        self.ip_entry = ttk.Entry(config_frame, width=15)
        self.port_label_tcp = ttk.Label(config_frame, text="Port:")
        self.port_entry_tcp = ttk.Entry(config_frame, width=10)

        ttk.Button(config_frame, text="Start Listening", command=self.start_listening).grid(column=0, row=2, columnspan=4, pady=5)

        self.status_label = ttk.Label(self.root, text="Status: Not listening", foreground="red")
        self.status_label.grid(column=0, row=1, padx=10, sticky="w")

        display_frame = ttk.LabelFrame(self.root, text="Data")
        display_frame.grid(column=0, row=2, padx=10, pady=10, sticky="nsew")

        ttk.Label(display_frame, text="Received Data:").grid(column=0, row=0, sticky="w")
        self.received_text = scrolledtext.ScrolledText(display_frame, width=80, height=10)
        self.received_text.grid(column=0, row=1, padx=5, pady=5)

        ttk.Label(display_frame, text="Data Sent:").grid(column=0, row=2, sticky="w")
        self.sent_text = scrolledtext.ScrolledText(display_frame, width=80, height=10)
        self.sent_text.grid(column=0, row=3, padx=5, pady=5)

        self.update_mode()

    def update_mode(self):
        mode = self.mode.get()
        if mode == "Serial":
            self.port_label.grid()
            self.port_combobox.grid()
            self.baud_label.grid()
            self.baud_entry.grid()
            self.ip_label.grid_remove()
            self.ip_entry.grid_remove()
            self.port_label_tcp.grid_remove()
            self.port_entry_tcp.grid_remove()
        else:
            self.port_label.grid_remove()
            self.port_combobox.grid_remove()
            self.baud_label.grid_remove()
            self.baud_entry.grid_remove()
            self.ip_label.grid(column=0, row=1, sticky="w")
            self.ip_entry.grid(column=1, row=1, sticky="w")
            self.port_label_tcp.grid(column=2, row=1, sticky="w")
            self.port_entry_tcp.grid(column=3, row=1, sticky="w")

    def detect_serial_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combobox['values'] = ports
        if ports:
            self.port_combobox.set(ports[0])

    def start_listening(self):
        self.running = True
        if self.mode.get() == "Serial":
            threading.Thread(target=self.listen_serial, daemon=True).start()
        else:
            threading.Thread(target=self.listen_tcp, daemon=True).start()

    def listen_serial(self):
        try:
            port = self.port_combobox.get()
            baudrate = int(self.baud_entry.get())
            self.serial_port = serial.Serial(port, baudrate, timeout=1)
            self.status_label.config(text=f"Listening on Serial {port} at {baudrate} baud", foreground="green")
            messagebox.showinfo("Listening", f"Listening on Serial {port} at {baudrate} baud")
            while self.running:
                if self.serial_port.in_waiting:
                    data = self.serial_port.readline().decode(errors='replace').strip()
                    self.display_received(data)
                    self.display_sent(data)
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground="red")
            messagebox.showerror("Error", str(e))

    def listen_tcp(self):
        try:
            ip = self.ip_entry.get()
            port = int(self.port_entry_tcp.get())
            self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_server.bind((ip, port))
            self.tcp_server.listen(5)
            self.status_label.config(text=f"Listening on TCP {ip}:{port}", foreground="green")
            messagebox.showinfo("Listening", f"Listening on TCP {ip}:{port}")
            while self.running:
                client_sock, addr = self.tcp_server.accept()
                thread = threading.Thread(target=self.handle_client, args=(client_sock,), daemon=True)
                thread.start()
                self.client_threads.append(thread)
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground="red")
            messagebox.showerror("Error", str(e))

    def handle_client(self, client_sock):
        with client_sock:
            while self.running:
                try:
                    data = client_sock.recv(4096)
                    if not data:
                        break
                    message = data.decode(errors='replace').strip()
                    self.display_received(message)
                    self.display_sent(message)
                except:
                    break

    def display_received(self, data):
        self.received_text.insert(tk.END, data + "\n")
        self.received_text.see(tk.END)

    def display_sent(self, data):
        self.sent_text.insert(tk.END, data + "\n")
        self.sent_text.see(tk.END)

if __name__ == '__main__':
    root = tk.Tk()
    app = DualModeListenerApp(root)
    root.mainloop()
