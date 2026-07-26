import socket
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import requests
import json
import os
import sys
from datetime import datetime


# ── Portable base directory (works both as .py and as .exe) ──────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)   # running as .exe
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # running as .py

SAVE_DIR = os.path.join(BASE_DIR, 'sent_messages')

# ── Color scheme ─────────────────────────────────────────────────────────────
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


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("HOSPI - LIS")
        self.root.configure(bg=COLORS['bg'])
        self.root.geometry("1200x800")

        self.server_running = False
        self.server_socket = None
        self.connection_counter = 0

        # Set window icon if icon.ico exists next to the .exe / script
        icon_path = os.path.join(BASE_DIR, 'icon.ico')
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass  # silently skip if icon can't be loaded

        os.makedirs(SAVE_DIR, exist_ok=True)

        self.setup_styles()
        self.create_status_bar()

        # ── Input fields ─────────────────────────────────────────────────────
        self.input_frame = tk.Frame(self.root, bg=COLORS['bg'])
        self.input_frame.pack(pady=15, padx=10, fill='x')

        # Row 1: IP and Port
        row1 = tk.Frame(self.input_frame, bg=COLORS['bg'])
        row1.pack(fill='x', pady=5)

        tk.Label(row1, text="IP:", bg=COLORS['bg'], fg=COLORS['fg'],
                 font=('Arial', 10, 'bold')).pack(side='left', padx=(0, 5))
        self.ip_entry = tk.Entry(row1, width=15, bg=COLORS['entry_bg'], fg=COLORS['fg'],
                                  insertbackground=COLORS['fg'], relief='flat', font=('Arial', 10))
        self.ip_entry.pack(side='left', padx=5, ipady=5)
        self.ip_entry.insert(0, '127.0.0.1')

        tk.Label(row1, text="Port:", bg=COLORS['bg'], fg=COLORS['fg'],
                 font=('Arial', 10, 'bold')).pack(side='left', padx=(15, 5))
        self.port_entry = tk.Entry(row1, width=8, bg=COLORS['entry_bg'], fg=COLORS['fg'],
                                    insertbackground=COLORS['fg'], relief='flat', font=('Arial', 10))
        self.port_entry.pack(side='left', padx=5, ipady=5)
        self.port_entry.insert(0, '5000')

        # Row 2: External URL
        row2 = tk.Frame(self.input_frame, bg=COLORS['bg'])
        row2.pack(fill='x', pady=5)

        tk.Label(row2, text="External URL:", bg=COLORS['bg'], fg=COLORS['fg'],
                 font=('Arial', 10, 'bold')).pack(side='left', padx=(0, 5))
        self.url_entry = tk.Entry(row2, bg=COLORS['entry_bg'], fg=COLORS['fg'],
                                   insertbackground=COLORS['fg'], relief='flat', font=('Arial', 10))
        self.url_entry.pack(side='left', fill='x', expand=True, padx=5, ipady=5)
        self.url_entry.insert(0, 'http://127.0.0.1:8003/api/hl7/receive')

        # Row 3: Save directory info label
        row3 = tk.Frame(self.input_frame, bg=COLORS['bg'])
        row3.pack(fill='x', pady=2)
        tk.Label(row3, text=f"💾 Saving messages to: {SAVE_DIR}",
                 bg=COLORS['bg'], fg=COLORS['warning'],
                 font=('Arial', 8)).pack(side='left', padx=(0, 5))

        # Row 4: Buttons
        button_frame = tk.Frame(self.input_frame, bg=COLORS['bg'])
        button_frame.pack(pady=10)

        self.start_button = tk.Button(
            button_frame, text="▶ Start Server", command=self.start_server,
            bg=COLORS['success'], fg='#000000', font=('Arial', 10, 'bold'),
            relief='flat', padx=20, pady=8, cursor='hand2')
        self.start_button.pack(side='left', padx=5)
        self.start_button.bind('<Enter>', lambda e: self.start_button.config(bg='#94e2d5'))
        self.start_button.bind('<Leave>', lambda e: self.start_button.config(bg=COLORS['success']))

        self.stop_button = tk.Button(
            button_frame, text="■ Stop Server", command=self.stop_server,
            bg=COLORS['error'], fg='#000000', font=('Arial', 10, 'bold'),
            relief='flat', padx=20, pady=8, cursor='hand2', state='disabled')
        self.stop_button.pack(side='left', padx=5)
        self.stop_button.bind('<Enter>', lambda e: self.stop_button.config(bg='#eba0ac') if self.server_running else None)
        self.stop_button.bind('<Leave>', lambda e: self.stop_button.config(bg=COLORS['error']) if self.server_running else None)

        # Open folder button
        self.folder_button = tk.Button(
            button_frame, text="📁 Open Save Folder", command=self.open_save_folder,
            bg=COLORS['button'], fg=COLORS['fg'], font=('Arial', 10),
            relief='flat', padx=15, pady=8, cursor='hand2')
        self.folder_button.pack(side='left', padx=5)
        self.folder_button.bind('<Enter>', lambda e: self.folder_button.config(bg=COLORS['button_hover']))
        self.folder_button.bind('<Leave>', lambda e: self.folder_button.config(bg=COLORS['button']))

        # ── Text display panels ───────────────────────────────────────────────
        self.received_frame = self.create_frame("Received Data")
        self.parsed_frame = self.create_frame("Formatted Data to Send")
        self.sent_frame = self.create_frame("Response from External URL")

    # ── UI helpers ────────────────────────────────────────────────────────────

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

    def create_status_bar(self):
        self.status_bar = tk.Frame(self.root, bg=COLORS['panel'], relief='flat', bd=0)
        self.status_bar.pack(side='bottom', fill='x')

        self.status_label = tk.Label(
            self.status_bar, text="● Offline", bg=COLORS['panel'],
            fg=COLORS['error'], font=('Arial', 9, 'bold'), anchor='w')
        self.status_label.pack(side='left', padx=10, pady=5)

        self.connection_count = tk.Label(
            self.status_bar, text="Connections: 0", bg=COLORS['panel'],
            fg=COLORS['fg'], font=('Arial', 9), anchor='e')
        self.connection_count.pack(side='right', padx=10, pady=5)

    def create_frame(self, title):
        container = tk.Frame(self.root, bg=COLORS['bg'])
        container.pack(fill="both", expand=True, padx=10, pady=5)

        frame = tk.LabelFrame(container, text=title, padx=10, pady=10,
                               bg=COLORS['label_frame'], fg=COLORS['accent'],
                               font=('Arial', 10, 'bold'), relief='flat', bd=2)
        frame.pack(fill="both", expand=True)

        btn_frame = tk.Frame(frame, bg=COLORS['label_frame'])
        btn_frame.pack(fill='x', pady=(0, 5))

        # Placeholder so lambda captures correct widget after creation
        text_widget_holder = [None]

        clear_btn = tk.Button(
            btn_frame, text="✕ Clear",
            command=lambda: self.clear_text(text_widget_holder[0]),
            bg=COLORS['button'], fg=COLORS['fg'], font=('Arial', 8),
            relief='flat', padx=10, pady=3, cursor='hand2')
        clear_btn.pack(side='right')
        clear_btn.bind('<Enter>', lambda e: clear_btn.config(bg=COLORS['button_hover']))
        clear_btn.bind('<Leave>', lambda e: clear_btn.config(bg=COLORS['button']))

        text_widget = tk.Text(
            frame, wrap=tk.WORD, height=10,
            bg=COLORS['entry_bg'], fg=COLORS['fg'],
            insertbackground=COLORS['fg'], relief='flat',
            font=('Consolas', 9), padx=10, pady=10,
            state=tk.DISABLED)
        text_widget.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(text_widget, command=text_widget.yview)
        scrollbar.pack(side='right', fill='y')
        text_widget.config(yscrollcommand=scrollbar.set)

        text_widget_holder[0] = text_widget
        return text_widget

    def clear_text(self, widget):
        widget.config(state=tk.NORMAL)
        widget.delete(1.0, tk.END)
        widget.config(state=tk.DISABLED)

    def update_text(self, widget, content):
        """Thread-safe text update."""
        def _update():
            widget.config(state=tk.NORMAL)
            widget.delete(1.0, tk.END)
            widget.insert(tk.END, content)
            widget.config(state=tk.DISABLED)
        self.root.after(0, _update)

    def open_save_folder(self):
        """Open the sent_messages folder in Windows Explorer."""
        os.makedirs(SAVE_DIR, exist_ok=True)
        os.startfile(SAVE_DIR)

    # ── Server logic ──────────────────────────────────────────────────────────

    def start_server(self):
        if self.server_running:
            messagebox.showinfo("Server Running", "Server is already running.")
            return

        ip = self.ip_entry.get().strip()
        url = self.url_entry.get().strip()

        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Port", "Port must be an integer.")
            return

        if not url.startswith("http"):
            messagebox.showerror("Invalid URL", "Please enter a valid HTTP/HTTPS URL.")
            return

        self.server_running = True
        self.external_url = url
        self.connection_counter = 0

        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.status_label.config(text=f"● Online — {ip}:{port}", fg=COLORS['success'])

        threading.Thread(target=self.run_server, args=(ip, port), daemon=True).start()
        self.update_text(self.received_frame, f"Listening on {ip}:{port}...\n")

    def stop_server(self):
        if not self.server_running:
            return

        self.server_running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.status_label.config(text="● Offline", fg=COLORS['error'])
        self.update_text(self.received_frame, "Server stopped.\n")

    def run_server(self, host, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((host, port))
            self.server_socket.listen()
        except Exception as e:
            self.update_text(self.received_frame, f"Error binding socket: {str(e)}")
            self.server_running = False
            self.root.after(0, lambda: self.start_button.config(state='normal'))
            self.root.after(0, lambda: self.stop_button.config(state='disabled'))
            self.root.after(0, lambda: self.status_label.config(text="● Offline", fg=COLORS['error']))
            return

        while self.server_running:
            try:
                self.server_socket.settimeout(1.0)
                client_socket, addr = self.server_socket.accept()
                self.connection_counter += 1
                self.root.after(0, lambda c=self.connection_counter:
                                self.connection_count.config(text=f"Connections: {c}"))
                threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr),
                    daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.server_running:
                    self.update_text(self.received_frame, f"Server error: {str(e)}")
                break

    def handle_client(self, conn, addr):
        with conn:
            try:
                data = conn.recv(4096)
                if not data:
                    return

                received_data = data.decode('utf-8', errors='ignore')
                self.update_text(self.received_frame, f"From {addr}:\n{received_data}")

                payload = {"data": received_data}
                formatted_json = json.dumps(payload, indent=4)
                self.update_text(self.parsed_frame, formatted_json)

                # Save to file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                filename = os.path.join(SAVE_DIR, f"message_{timestamp}.json")
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(payload, f, indent=4)
                except Exception as e:
                    print(f"Error saving file: {e}")

                # Forward to external API
                try:
                    headers = {'Content-Type': 'application/json'}
                    response = requests.post(self.external_url, json=payload,
                                             headers=headers, timeout=10)
                    result = (f"Status Code: {response.status_code}\n"
                              f"Response:\n{response.text}")
                except Exception as e:
                    result = f"Failed to send data:\n{str(e)}"

                self.update_text(self.sent_frame, result)

            except Exception as e:
                self.update_text(self.received_frame, f"Client error: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
