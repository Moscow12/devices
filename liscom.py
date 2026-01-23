import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import socket
import threading
import requests
import json
import os
from datetime import datetime

SAVE_DIR = 'logs'

# Color scheme (matching lis.py)
COLORS = {
    'bg': '#1e1e2e',
    'fg': '#cdd6f4',
    'accent': '#89b4fa',
    'success': '#a6e3a1',
    'error': '#f38ba8',
    'warning': '#fab387',
    'panel': '#313244',
    'button': '#45475a',
    'button_hover': '#585b70',
    'entry_bg': '#181825',
    'label_frame': '#313244'
}


class SerialTcpApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TS-LISA")
        self.root.configure(bg=COLORS['bg'])
        self.root.geometry("1200x900")

        self.serial_port = None
        self.server_socket = None
        self.running = False
        self.connection_counter = 0
        os.makedirs(SAVE_DIR, exist_ok=True)

        # Configure style
        self.setup_styles()

        # Status bar
        self.create_status_bar()

        # Mode selection
        self.create_mode_selector()

        # Configuration frames (will be shown/hidden based on mode)
        self.create_serial_config()
        self.create_tcp_config()

        # API URL (common for both modes)
        self.create_api_config()

        # Control buttons
        self.create_control_buttons()

        # Text display areas
        self.received_text = self.create_frame("Received Data")
        self.sent_text = self.create_frame("Formatted Data to Send")
        self.response_text = self.create_frame("API Response")

        # Initial setup
        self.refresh_ports()
        self.toggle_mode()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

    def create_status_bar(self):
        self.status_bar = tk.Frame(self.root, bg=COLORS['panel'], relief='flat', bd=0)
        self.status_bar.pack(side='bottom', fill='x')

        self.status_label = tk.Label(self.status_bar, text="● Offline", bg=COLORS['panel'],
                                     fg=COLORS['error'], font=('Arial', 9, 'bold'), anchor='w')
        self.status_label.pack(side='left', padx=10, pady=5)

        self.connection_count = tk.Label(self.status_bar, text="Connections: 0", bg=COLORS['panel'],
                                        fg=COLORS['fg'], font=('Arial', 9), anchor='e')
        self.connection_count.pack(side='right', padx=10, pady=5)

    def create_mode_selector(self):
        self.mode_frame = tk.Frame(self.root, bg=COLORS['bg'])
        self.mode_frame.pack(pady=10, padx=10, fill='x')

        tk.Label(self.mode_frame, text="Mode:", bg=COLORS['bg'], fg=COLORS['accent'],
                font=('Arial', 11, 'bold')).pack(side='left', padx=(0, 10))

        self.mode_var = tk.StringVar(value="serial")

        serial_radio = tk.Radiobutton(self.mode_frame, text="📡 Serial Port", variable=self.mode_var,
                                     value="serial", command=self.toggle_mode,
                                     bg=COLORS['bg'], fg=COLORS['fg'], selectcolor=COLORS['panel'],
                                     font=('Arial', 10), activebackground=COLORS['bg'],
                                     activeforeground=COLORS['accent'], cursor='hand2')
        serial_radio.pack(side='left', padx=5)

        tcp_radio = tk.Radiobutton(self.mode_frame, text="🌐 TCP Socket", variable=self.mode_var,
                                  value="tcp", command=self.toggle_mode,
                                  bg=COLORS['bg'], fg=COLORS['fg'], selectcolor=COLORS['panel'],
                                  font=('Arial', 10), activebackground=COLORS['bg'],
                                  activeforeground=COLORS['accent'], cursor='hand2')
        tcp_radio.pack(side='left', padx=5)

    def create_serial_config(self):
        self.serial_frame = tk.Frame(self.root, bg=COLORS['bg'])
        self.serial_frame.pack(pady=5, padx=10, fill='x')

        # Row 1: Port selection
        row1 = tk.Frame(self.serial_frame, bg=COLORS['bg'])
        row1.pack(fill='x', pady=5)

        tk.Label(row1, text="Port:", bg=COLORS['bg'], fg=COLORS['fg'],
                font=('Arial', 10, 'bold')).pack(side='left', padx=(0, 5))

        self.port_combobox = ttk.Combobox(row1, width=12, font=('Arial', 10))
        self.port_combobox.pack(side='left', padx=5)

        refresh_btn = tk.Button(row1, text="🔄 Refresh", command=self.refresh_ports,
                               bg=COLORS['button'], fg=COLORS['fg'], font=('Arial', 9),
                               relief='flat', padx=10, pady=5, cursor='hand2')
        refresh_btn.pack(side='left', padx=5)
        refresh_btn.bind('<Enter>', lambda e: refresh_btn.config(bg=COLORS['button_hover']))
        refresh_btn.bind('<Leave>', lambda e: refresh_btn.config(bg=COLORS['button']))

        self.port_status = tk.Label(row1, text="Detecting...", bg=COLORS['bg'],
                                   fg=COLORS['warning'], font=('Arial', 9))
        self.port_status.pack(side='left', padx=10)

        tk.Label(row1, text="Baudrate:", bg=COLORS['bg'], fg=COLORS['fg'],
                font=('Arial', 10, 'bold')).pack(side='left', padx=(20, 5))

        self.baud_entry = tk.Entry(row1, width=10, bg=COLORS['entry_bg'], fg=COLORS['fg'],
                                  insertbackground=COLORS['fg'], relief='flat', font=('Arial', 10))
        self.baud_entry.pack(side='left', padx=5, ipady=5)
        self.baud_entry.insert(0, '9600')

    def create_tcp_config(self):
        self.tcp_frame = tk.Frame(self.root, bg=COLORS['bg'])
        self.tcp_frame.pack(pady=5, padx=10, fill='x')

        # Row 1: IP and Port
        row1 = tk.Frame(self.tcp_frame, bg=COLORS['bg'])
        row1.pack(fill='x', pady=5)

        tk.Label(row1, text="IP:", bg=COLORS['bg'], fg=COLORS['fg'],
                font=('Arial', 10, 'bold')).pack(side='left', padx=(0, 5))

        self.ip_entry = tk.Entry(row1, width=15, bg=COLORS['entry_bg'], fg=COLORS['fg'],
                                insertbackground=COLORS['fg'], relief='flat', font=('Arial', 10))
        self.ip_entry.pack(side='left', padx=5, ipady=5)
        self.ip_entry.insert(0, '127.0.0.1')

        tk.Label(row1, text="Port:", bg=COLORS['bg'], fg=COLORS['fg'],
                font=('Arial', 10, 'bold')).pack(side='left', padx=(15, 5))

        self.tcp_port_entry = tk.Entry(row1, width=8, bg=COLORS['entry_bg'], fg=COLORS['fg'],
                                       insertbackground=COLORS['fg'], relief='flat', font=('Arial', 10))
        self.tcp_port_entry.pack(side='left', padx=5, ipady=5)
        self.tcp_port_entry.insert(0, '5000')

    def create_api_config(self):
        api_frame = tk.Frame(self.root, bg=COLORS['bg'])
        api_frame.pack(pady=5, padx=10, fill='x')

        tk.Label(api_frame, text="API URL:", bg=COLORS['bg'], fg=COLORS['fg'],
                font=('Arial', 10, 'bold')).pack(side='left', padx=(0, 5))

        self.url_entry = tk.Entry(api_frame, bg=COLORS['entry_bg'], fg=COLORS['fg'],
                                 insertbackground=COLORS['fg'], relief='flat', font=('Arial', 10))
        self.url_entry.pack(side='left', fill='x', expand=True, padx=5, ipady=5)
        self.url_entry.insert(0, 'http://127.0.0.1:8003/api/hl7/receive')

    def create_control_buttons(self):
        button_frame = tk.Frame(self.root, bg=COLORS['bg'])
        button_frame.pack(pady=15)

        self.start_button = tk.Button(button_frame, text="▶ Start Listening", command=self.start_listening,
                                      bg=COLORS['success'], fg='#000000', font=('Arial', 10, 'bold'),
                                      relief='flat', padx=20, pady=8, cursor='hand2')
        self.start_button.pack(side='left', padx=5)
        self.start_button.bind('<Enter>', lambda e: self.start_button.config(bg='#94e2d5'))
        self.start_button.bind('<Leave>', lambda e: self.start_button.config(bg=COLORS['success']))

        self.stop_button = tk.Button(button_frame, text="■ Stop Listening", command=self.stop_listening,
                                     bg=COLORS['error'], fg='#000000', font=('Arial', 10, 'bold'),
                                     relief='flat', padx=20, pady=8, cursor='hand2', state='disabled')
        self.stop_button.pack(side='left', padx=5)
        self.stop_button.bind('<Enter>', lambda e: self.stop_button.config(bg='#eba0ac') if self.running else None)
        self.stop_button.bind('<Leave>', lambda e: self.stop_button.config(bg=COLORS['error']) if self.running else None)

    def create_frame(self, title):
        container = tk.Frame(self.root, bg=COLORS['bg'])
        container.pack(fill="both", expand=True, padx=10, pady=5)

        frame = tk.LabelFrame(container, text=title, padx=10, pady=10,
                             bg=COLORS['label_frame'], fg=COLORS['accent'],
                             font=('Arial', 10, 'bold'), relief='flat', bd=2)
        frame.pack(fill="both", expand=True)

        # Button frame for clear button
        btn_frame = tk.Frame(frame, bg=COLORS['label_frame'])
        btn_frame.pack(fill='x', pady=(0, 5))

        clear_btn = tk.Button(btn_frame, text="✕ Clear", command=lambda: self.clear_text(text_widget),
                             bg=COLORS['button'], fg=COLORS['fg'], font=('Arial', 8),
                             relief='flat', padx=10, pady=3, cursor='hand2')
        clear_btn.pack(side='right')
        clear_btn.bind('<Enter>', lambda e: clear_btn.config(bg=COLORS['button_hover']))
        clear_btn.bind('<Leave>', lambda e: clear_btn.config(bg=COLORS['button']))

        text_widget = tk.Text(frame, wrap=tk.WORD, height=8,
                             bg=COLORS['entry_bg'], fg=COLORS['fg'],
                             insertbackground=COLORS['fg'], relief='flat',
                             font=('Consolas', 9), padx=10, pady=10)
        text_widget.pack(fill="both", expand=True)

        # Add scrollbar
        scrollbar = tk.Scrollbar(text_widget, command=text_widget.yview)
        scrollbar.pack(side='right', fill='y')
        text_widget.config(yscrollcommand=scrollbar.set)

        return text_widget

    def clear_text(self, widget):
        widget.config(state=tk.NORMAL)
        widget.delete(1.0, tk.END)
        widget.config(state=tk.DISABLED)

    def update_text(self, widget, content):
        widget.config(state=tk.NORMAL)
        widget.insert(tk.END, content + "\n")
        widget.see(tk.END)
        widget.config(state=tk.DISABLED)

    def toggle_mode(self):
        mode = self.mode_var.get()
        if mode == "serial":
            self.serial_frame.pack(pady=5, padx=10, fill='x', after=self.mode_frame)
            self.tcp_frame.pack_forget()
        else:
            self.tcp_frame.pack(pady=5, padx=10, fill='x', after=self.mode_frame)
            self.serial_frame.pack_forget()

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combobox['values'] = ports
        if ports:
            self.port_combobox.set(ports[0])
            self.port_status.config(text=f"Detected: {ports[0]}", fg=COLORS['success'])
        else:
            self.port_combobox.set('')
            self.port_status.config(text="No serial ports detected", fg=COLORS['error'])

    def start_listening(self):
        if self.running:
            messagebox.showinfo("Already Running", "Listener is already active.")
            return

        mode = self.mode_var.get()
        url = self.url_entry.get()

        if not url.startswith("http"):
            messagebox.showerror("Invalid URL", "Please enter a valid HTTP/HTTPS URL.")
            return

        self.external_url = url
        self.running = True
        self.connection_counter = 0

        # Update UI
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')

        if mode == "serial":
            self.start_serial()
        else:
            self.start_tcp()

    def start_serial(self):
        try:
            port = self.port_combobox.get()
            baud = int(self.baud_entry.get())

            if not port:
                raise ValueError("No serial port selected")

            self.serial_port = serial.Serial(port, baud, timeout=1)
            self.status_label.config(text=f"● Serial Active - {port}@{baud}", fg=COLORS['success'])
            self.update_text(self.received_text, f"Listening on serial port {port} at {baud} baud...")

            threading.Thread(target=self.read_serial, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Serial Error", str(e))
            self.stop_listening()

    def start_tcp(self):
        ip = self.ip_entry.get()
        try:
            port = int(self.tcp_port_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Port", "Port must be an integer.")
            self.stop_listening()
            return

        self.status_label.config(text=f"● TCP Active - {ip}:{port}", fg=COLORS['success'])
        self.update_text(self.received_text, f"Listening on TCP {ip}:{port}...")

        threading.Thread(target=self.run_tcp_server, args=(ip, port), daemon=True).start()

    def stop_listening(self):
        self.running = False

        # Close serial port
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

        # Close TCP socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        # Update UI
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.status_label.config(text="● Offline", fg=COLORS['error'])
        self.update_text(self.received_text, "Stopped listening.")

    def read_serial(self):
        while self.running:
            try:
                if self.serial_port.in_waiting:
                    data = self.serial_port.readline().decode(errors='ignore').strip()
                    if data:
                        self.update_text(self.received_text, f"Serial: {data}")
                        self.forward_data(data)
                        self.connection_counter += 1
                        self.connection_count.config(text=f"Messages: {self.connection_counter}")
            except Exception as e:
                if self.running:
                    self.update_text(self.received_text, f"Serial error: {e}")
                break

    def run_tcp_server(self, host, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((host, port))
            self.server_socket.listen()
        except Exception as e:
            self.update_text(self.received_text, f"Error binding socket: {str(e)}")
            self.running = False
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.status_label.config(text="● Offline", fg=COLORS['error'])
            return

        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                client_socket, addr = self.server_socket.accept()
                self.connection_counter += 1
                self.connection_count.config(text=f"Connections: {self.connection_counter}")
                threading.Thread(target=self.handle_tcp_client, args=(client_socket, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.update_text(self.received_text, f"Server error: {str(e)}")
                break

    def handle_tcp_client(self, conn, addr):
        with conn:
            try:
                data = conn.recv(4096)
                if not data:
                    return

                received_data = data.decode('utf-8', errors='ignore')
                self.update_text(self.received_text, f"From {addr}: {received_data}")
                self.forward_data(received_data)
            except Exception as e:
                self.update_text(self.received_text, f"Client error: {str(e)}")

    def forward_data(self, data):
        # Format as JSON
        json_data = {"data": data}
        formatted_json = json.dumps(json_data, indent=2)
        self.update_text(self.sent_text, formatted_json)

        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = os.path.join(SAVE_DIR, f"sent_{timestamp}.json")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2)
        except Exception as e:
            print(f"Error saving file: {e}")

        # Send to external API
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(self.external_url, json=json_data, headers=headers, timeout=5)
            result = f"Status: {response.status_code}\n{response.text}"

            # Save response
            response_file = os.path.join(SAVE_DIR, f"response_{timestamp}.json")
            try:
                with open(response_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
            except:
                pass

        except Exception as e:
            result = f"API Error: {str(e)}"

        self.update_text(self.response_text, result)


if __name__ == "__main__":
    root = tk.Tk()
    app = SerialTcpApp(root)
    root.mainloop()
