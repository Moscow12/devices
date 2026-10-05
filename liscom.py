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
CONFIG_FILE = 'liscom_config.json'
DATA_LOG_FILE = os.path.join(SAVE_DIR, 'machine_data.log')
SENT_LOG_FILE = os.path.join(SAVE_DIR, 'sent_data.log')
RESPONSE_LOG_FILE = os.path.join(SAVE_DIR, 'api_responses.log')
# If set, this environment variable overrides the API key saved in the config file
API_KEY_ENV = 'LISCOM_API_KEY'

os.makedirs(SAVE_DIR, exist_ok=True)

_log_lock = threading.Lock()


def _append_log(path, source, data):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with _log_lock:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] [{source}] {data}\n")


def log_machine_data(source, data):
    _append_log(DATA_LOG_FILE, source, data)


def log_sent_data(source, data):
    _append_log(SENT_LOG_FILE, f"SENT {source}", data)


def log_api_response(source, status_code, body):
    _append_log(RESPONSE_LOG_FILE, f"RESPONSE {source}", f"Status {status_code}: {body}")

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
        self.root.title("TS - LIS")
        self.root.configure(bg=COLORS['bg'])
        self.root.geometry("1200x900")

        self.serial_port = None
        self.serial_port_name = None
        self.serial_baud = None
        self.server_socket = None
        self.running = False
        self.serial_active = False
        self.tcp_active = False
        self.serial_count = 0
        self.tcp_count = 0
        self.counter_lock = threading.Lock()
        self.external_url = ''
        self.api_key = ''
        os.makedirs(SAVE_DIR, exist_ok=True)

        # Configure style
        self.setup_styles()

        # Status bar
        self.create_status_bar()

        # Configuration frames (both channels can run at the same time)
        self.create_serial_config()
        self.create_tcp_config()

        # API URL (common for both channels)
        self.create_api_config()

        # Control buttons
        self.create_control_buttons()

        # Text display areas
        self.received_text = self.create_frame("Received Data")
        self.sent_text = self.create_frame("Formatted Data to Send")
        self.response_text = self.create_frame("API Response")

        # Initial setup
        self.refresh_ports()
        self.load_config()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

    # ------------------------------------------------------------------ UI helpers

    def run_on_ui(self, func, *args, **kwargs):
        """Run func on the Tk main thread (Tk widgets are not thread-safe)."""
        if threading.current_thread() is threading.main_thread():
            func(*args, **kwargs)
        else:
            self.root.after(0, lambda: func(*args, **kwargs))

    def set_label(self, label, text, color):
        self.run_on_ui(label.config, text=text, fg=color)

    def create_status_bar(self):
        self.status_bar = tk.Frame(self.root, bg=COLORS['panel'], relief='flat', bd=0)
        self.status_bar.pack(side='bottom', fill='x')

        self.serial_status_label = tk.Label(self.status_bar, text="Serial: ● Offline", bg=COLORS['panel'],
                                            fg=COLORS['error'], font=('Arial', 9, 'bold'), anchor='w')
        self.serial_status_label.pack(side='left', padx=10, pady=5)

        self.tcp_status_label = tk.Label(self.status_bar, text="TCP: ● Offline", bg=COLORS['panel'],
                                         fg=COLORS['error'], font=('Arial', 9, 'bold'), anchor='w')
        self.tcp_status_label.pack(side='left', padx=10, pady=5)

        self.connection_count = tk.Label(self.status_bar, text="Serial messages: 0 | TCP connections: 0",
                                         bg=COLORS['panel'], fg=COLORS['fg'], font=('Arial', 9), anchor='e')
        self.connection_count.pack(side='right', padx=10, pady=5)

    def update_counts(self):
        with self.counter_lock:
            text = f"Serial messages: {self.serial_count} | TCP connections: {self.tcp_count}"
        self.run_on_ui(self.connection_count.config, text=text)

    def create_checkbox(self, parent, text, variable):
        return tk.Checkbutton(parent, text=text, variable=variable,
                              bg=COLORS['bg'], fg=COLORS['fg'], selectcolor=COLORS['panel'],
                              font=('Arial', 10, 'bold'), activebackground=COLORS['bg'],
                              activeforeground=COLORS['accent'], cursor='hand2')

    def create_serial_config(self):
        self.serial_frame = tk.Frame(self.root, bg=COLORS['bg'])
        self.serial_frame.pack(pady=5, padx=10, fill='x')

        row1 = tk.Frame(self.serial_frame, bg=COLORS['bg'])
        row1.pack(fill='x', pady=5)

        self.serial_enabled = tk.BooleanVar(value=True)
        self.serial_check = self.create_checkbox(row1, "📡 Serial", self.serial_enabled)
        self.serial_check.config(width=10, anchor='w')
        self.serial_check.pack(side='left', padx=(0, 10))

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

        row1 = tk.Frame(self.tcp_frame, bg=COLORS['bg'])
        row1.pack(fill='x', pady=5)

        self.tcp_enabled = tk.BooleanVar(value=True)
        self.tcp_check = self.create_checkbox(row1, "🌐 TCP", self.tcp_enabled)
        self.tcp_check.config(width=10, anchor='w')
        self.tcp_check.pack(side='left', padx=(0, 10))

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
        self.url_entry.insert(0, 'http://127.0.0.1:8003/api/hl7/receive-results')

        # API key sent as `X-API-Key` (must match HL7_API_KEY on the receiving system)
        key_frame = tk.Frame(self.root, bg=COLORS['bg'])
        key_frame.pack(pady=5, padx=10, fill='x')

        tk.Label(key_frame, text="API Key:", bg=COLORS['bg'], fg=COLORS['fg'],
                font=('Arial', 10, 'bold')).pack(side='left', padx=(0, 5))

        self.api_key_entry = tk.Entry(key_frame, show='•', bg=COLORS['entry_bg'], fg=COLORS['fg'],
                                      insertbackground=COLORS['fg'], relief='flat', font=('Arial', 10))
        self.api_key_entry.pack(side='left', fill='x', expand=True, padx=5, ipady=5)

        self.show_key_btn = tk.Button(key_frame, text="👁 Show", command=self.toggle_key_visibility,
                                      bg=COLORS['button'], fg=COLORS['fg'], font=('Arial', 9),
                                      relief='flat', padx=10, pady=5, cursor='hand2')
        self.show_key_btn.pack(side='left', padx=5)

        self.key_source_label = tk.Label(key_frame, text="", bg=COLORS['bg'],
                                         fg=COLORS['warning'], font=('Arial', 9))
        self.key_source_label.pack(side='left', padx=5)
        if os.environ.get(API_KEY_ENV):
            self.key_source_label.config(text=f"Using {API_KEY_ENV} from environment")

    def toggle_key_visibility(self):
        if self.api_key_entry.cget('show'):
            self.api_key_entry.config(show='')
            self.show_key_btn.config(text="🙈 Hide")
        else:
            self.api_key_entry.config(show='•')
            self.show_key_btn.config(text="👁 Show")

    def get_api_key(self):
        return (os.environ.get(API_KEY_ENV) or self.api_key_entry.get()).strip()

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

        save_config_button = tk.Button(button_frame, text="💾 Save Configuration", command=self.save_config,
                                       bg=COLORS['accent'], fg='#000000', font=('Arial', 10, 'bold'),
                                       relief='flat', padx=20, pady=8, cursor='hand2')
        save_config_button.pack(side='left', padx=5)
        save_config_button.bind('<Enter>', lambda e: save_config_button.config(bg='#b4befe'))
        save_config_button.bind('<Leave>', lambda e: save_config_button.config(bg=COLORS['accent']))

    # ------------------------------------------------------------------ configuration

    def get_config(self):
        return {
            'serial_enabled': self.serial_enabled.get(),
            'tcp_enabled': self.tcp_enabled.get(),
            'port': self.port_combobox.get(),
            'baud': self.baud_entry.get(),
            'ip': self.ip_entry.get(),
            'tcp_port': self.tcp_port_entry.get(),
            'url': self.url_entry.get(),
            'api_key': self.api_key_entry.get().strip(),
        }

    def save_config(self, silent=False):
        try:
            # The file holds the API key, so create it readable by the owner only
            fd = os.open(CONFIG_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(self.get_config(), f, indent=2)
            if not silent:
                messagebox.showinfo("Configuration Saved", f"Configuration saved to {CONFIG_FILE}")
        except Exception as e:
            if silent:
                print(f"Error saving config: {e}")
            else:
                messagebox.showerror("Save Error", f"Failed to save configuration: {e}")

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return

        if 'serial_enabled' in config or 'tcp_enabled' in config:
            self.serial_enabled.set(bool(config.get('serial_enabled', True)))
            self.tcp_enabled.set(bool(config.get('tcp_enabled', True)))
        elif 'mode' in config:
            # Backward compatibility with the old single-mode config
            self.serial_enabled.set(config['mode'] == 'serial')
            self.tcp_enabled.set(config['mode'] == 'tcp')

        port = config.get('port', '')
        if port:
            self.port_combobox.set(port)

        for entry, key in ((self.baud_entry, 'baud'), (self.ip_entry, 'ip'),
                           (self.tcp_port_entry, 'tcp_port'), (self.url_entry, 'url'),
                           (self.api_key_entry, 'api_key')):
            value = config.get(key)
            if value:
                entry.delete(0, tk.END)
                entry.insert(0, value)

    # ------------------------------------------------------------------ text areas

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

    def _insert_text(self, widget, content):
        widget.config(state=tk.NORMAL)
        widget.insert(tk.END, content + "\n")
        widget.see(tk.END)
        widget.config(state=tk.DISABLED)

    def update_text(self, widget, content):
        self.run_on_ui(self._insert_text, widget, content)

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combobox['values'] = ports
        current = self.port_combobox.get()
        if ports:
            if current not in ports:
                self.port_combobox.set(ports[0])
            self.port_status.config(text=f"Detected: {self.port_combobox.get()}", fg=COLORS['success'])
        else:
            self.port_combobox.set('')
            self.port_status.config(text="No serial ports detected", fg=COLORS['error'])

    # ------------------------------------------------------------------ start / stop

    def start_listening(self):
        if self.running:
            messagebox.showinfo("Already Running", "Listener is already active.")
            return

        use_serial = self.serial_enabled.get()
        use_tcp = self.tcp_enabled.get()
        if not (use_serial or use_tcp):
            messagebox.showerror("Nothing Enabled", "Enable Serial, TCP, or both.")
            return

        url = self.url_entry.get()
        if not url.startswith("http"):
            messagebox.showerror("Invalid URL", "Please enter a valid HTTP/HTTPS URL.")
            return

        api_key = self.get_api_key()
        if not api_key and not messagebox.askyesno(
                "No API Key",
                "No API key is set, so the receiving system will reject results (401).\n\n"
                "Start anyway?"):
            return

        self.save_config(silent=True)

        self.external_url = url
        self.api_key = api_key
        self.running = True
        with self.counter_lock:
            self.serial_count = 0
            self.tcp_count = 0
        self.update_counts()

        # Update UI
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.serial_check.config(state='disabled')
        self.tcp_check.config(state='disabled')

        # Each channel starts independently; one failing doesn't stop the other
        if use_serial:
            self.start_serial()
        if use_tcp:
            self.start_tcp()

        if not (self.serial_active or self.tcp_active):
            self.stop_listening()

    def start_serial(self):
        try:
            port = self.port_combobox.get()
            baud = int(self.baud_entry.get())

            available = [p.device for p in serial.tools.list_ports.comports()]
            if port not in available:
                self.refresh_ports()
                port = self.port_combobox.get()
                if port:
                    self.update_text(self.received_text, f"Port changed, now using {port}")

            if not port:
                raise ValueError("No serial port selected")

            self.serial_baud = baud
            self.serial_port_name = port
            self.serial_port = serial.Serial(port, baud, timeout=1)
            self.serial_active = True
            self.set_label(self.serial_status_label, f"Serial: ● Active - {port}@{baud}", COLORS['success'])
            self.update_text(self.received_text, f"Listening on serial port {port} at {baud} baud...")

            threading.Thread(target=self.read_serial, daemon=True).start()
        except Exception as e:
            self.serial_active = False
            self.set_label(self.serial_status_label, "Serial: ● Failed", COLORS['error'])
            messagebox.showerror("Serial Error", str(e))

    def start_tcp(self):
        ip = self.ip_entry.get()
        try:
            port = int(self.tcp_port_entry.get())
        except ValueError:
            self.set_label(self.tcp_status_label, "TCP: ● Failed", COLORS['error'])
            messagebox.showerror("Invalid Port", "TCP port must be an integer.")
            return

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((ip, port))
            self.server_socket.listen()
            self.server_socket.settimeout(1.0)
        except Exception as e:
            self.close_server_socket()
            self.set_label(self.tcp_status_label, "TCP: ● Failed", COLORS['error'])
            self.update_text(self.received_text, f"Error binding socket: {e}")
            messagebox.showerror("TCP Error", f"Could not listen on {ip}:{port}\n{e}")
            return

        self.tcp_active = True
        self.set_label(self.tcp_status_label, f"TCP: ● Active - {ip}:{port}", COLORS['success'])
        self.update_text(self.received_text, f"Listening on TCP {ip}:{port}...")

        threading.Thread(target=self.run_tcp_server, daemon=True).start()

    def close_server_socket(self):
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None

    def stop_listening(self):
        was_running = self.running
        self.running = False
        self.serial_active = False
        self.tcp_active = False

        # Close serial port
        if self.serial_port:
            try:
                self.serial_port.close()
            except Exception:
                pass
            self.serial_port = None

        # Close TCP socket
        self.close_server_socket()

        # Update UI
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.serial_check.config(state='normal')
        self.tcp_check.config(state='normal')
        self.serial_status_label.config(text="Serial: ● Offline", fg=COLORS['error'])
        self.tcp_status_label.config(text="TCP: ● Offline", fg=COLORS['error'])
        if was_running:
            self.update_text(self.received_text, "Stopped listening.")

    def channel_stopped(self):
        """Called (on the UI thread) when a channel dies; stop fully if none remain."""
        if self.running and not (self.serial_active or self.tcp_active):
            self.stop_listening()

    def on_close(self):
        self.save_config(silent=True)
        self.stop_listening()
        self.root.destroy()

    # ------------------------------------------------------------------ serial

    def reopen_serial_port(self):
        available = [p.device for p in serial.tools.list_ports.comports()]
        current = self.serial_port_name
        port = current if current in available else (available[0] if available else None)

        if not port:
            return False

        try:
            if self.serial_port:
                try:
                    self.serial_port.close()
                except Exception:
                    pass
            self.serial_port = serial.Serial(port, self.serial_baud, timeout=1)
            self.serial_port_name = port
            self.run_on_ui(self.port_combobox.set, port)
            self.set_label(self.port_status, f"Detected: {port}", COLORS['success'])
            self.set_label(self.serial_status_label, f"Serial: ● Active - {port}@{self.serial_baud}",
                           COLORS['success'])
            self.update_text(self.received_text, f"Reconnected on serial port {port}")
            return True
        except Exception:
            return False

    def read_serial(self):
        while self.running and self.serial_active:
            try:
                raw = self.serial_port.readline()  # returns b'' after the 1s timeout
                data = raw.decode(errors='ignore').strip()
                if data:
                    log_machine_data("Serial", data)
                    self.update_text(self.received_text, f"[Serial] {data}")
                    with self.counter_lock:
                        self.serial_count += 1
                    self.update_counts()
                    self.forward_data("Serial", data)
            except (serial.SerialException, OSError) as e:
                if not (self.running and self.serial_active):
                    break
                self.update_text(self.received_text, f"Serial port disconnected ({e}), reconnecting...")
                self.set_label(self.serial_status_label, "Serial: ● Reconnecting...", COLORS['warning'])
                while self.running and self.serial_active and not self.reopen_serial_port():
                    threading.Event().wait(2)
            except Exception as e:
                if self.running and self.serial_active:
                    self.update_text(self.received_text, f"Serial error: {e}")
                    self.serial_active = False
                    self.set_label(self.serial_status_label, "Serial: ● Stopped (error)", COLORS['error'])
                    self.run_on_ui(self.channel_stopped)
                break

    # ------------------------------------------------------------------ TCP

    def run_tcp_server(self):
        server = self.server_socket
        while self.running and self.tcp_active:
            try:
                client_socket, addr = server.accept()
                with self.counter_lock:
                    self.tcp_count += 1
                self.update_counts()
                threading.Thread(target=self.handle_tcp_client, args=(client_socket, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running and self.tcp_active:
                    self.update_text(self.received_text, f"Server error: {e}")
                    self.tcp_active = False
                    self.set_label(self.tcp_status_label, "TCP: ● Stopped (error)", COLORS['error'])
                    self.run_on_ui(self.channel_stopped)
                break

    def handle_tcp_client(self, conn, addr):
        source = f"TCP {addr[0]}:{addr[1]}"
        with conn:
            conn.settimeout(1.0)
            # Keep reading until the client disconnects, so persistent connections work
            while self.running and self.tcp_active:
                try:
                    data = conn.recv(4096)
                except socket.timeout:
                    continue
                except Exception as e:
                    self.update_text(self.received_text, f"Client error ({source}): {e}")
                    break
                if not data:
                    break

                received_data = data.decode('utf-8', errors='ignore')
                log_machine_data(source, received_data)
                self.update_text(self.received_text, f"[{source}] {received_data}")
                self.forward_data(source, received_data)

    # ------------------------------------------------------------------ API

    def forward_data(self, source, data):
        # Format as JSON
        json_data = {"data": data}
        formatted_json = json.dumps(json_data, indent=2)
        self.update_text(self.sent_text, f"[{source}]\n{formatted_json}")
        log_sent_data(source, formatted_json)

        # Send to external API
        try:
            headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
            if self.api_key:
                headers['X-API-Key'] = self.api_key
            response = requests.post(self.external_url, json=json_data, headers=headers, timeout=5)
            result = f"[{source}] Status: {response.status_code}\n{response.text}"
            if response.status_code == 401:
                result += "\n⚠ Unauthorized: the API key is missing or does not match HL7_API_KEY."
            elif response.status_code == 403:
                result += "\n⚠ Forbidden: this computer's IP is not in HL7_ALLOWED_IPS."
            log_api_response(source, response.status_code, response.text)
        except Exception as e:
            result = f"[{source}] API Error: {e}"
            log_api_response(source, "ERROR", str(e))

        self.update_text(self.response_text, result)


if __name__ == "__main__":
    root = tk.Tk()
    app = SerialTcpApp(root)
    root.mainloop()
