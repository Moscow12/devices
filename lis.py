import socket
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import requests
import json
import os
from datetime import datetime


SAVE_DIR = 'sent_messages'

# Color scheme
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
        self.root.title("TS-LIS Listener")
        self.root.configure(bg=COLORS['bg'])
        self.root.geometry("1200x800")

        self.server_running = False
        self.server_socket = None
        os.makedirs(SAVE_DIR, exist_ok=True)

        # Configure style
        self.setup_styles()

        # Status bar
        self.create_status_bar()

        # Input fields: IP, Port, External URL
        self.input_frame = tk.Frame(self.root, bg=COLORS['bg'])
        self.input_frame.pack(pady=15, padx=10, fill='x')

        # Row 1: IP and Port
        row1 = tk.Frame(self.input_frame, bg=COLORS['bg'])
        row1.pack(fill='x', pady=5)

        tk.Label(row1, text="IP:", bg=COLORS['bg'], fg=COLORS['fg'], font=('Arial', 10, 'bold')).pack(side='left', padx=(0, 5))
        self.ip_entry = tk.Entry(row1, width=15, bg=COLORS['entry_bg'], fg=COLORS['fg'], insertbackground=COLORS['fg'], relief='flat', font=('Arial', 10))
        self.ip_entry.pack(side='left', padx=5, ipady=5)
        self.ip_entry.insert(0, '127.0.0.1')

        tk.Label(row1, text="Port:", bg=COLORS['bg'], fg=COLORS['fg'], font=('Arial', 10, 'bold')).pack(side='left', padx=(15, 5))
        self.port_entry = tk.Entry(row1, width=8, bg=COLORS['entry_bg'], fg=COLORS['fg'], insertbackground=COLORS['fg'], relief='flat', font=('Arial', 10))
        self.port_entry.pack(side='left', padx=5, ipady=5)
        self.port_entry.insert(0, '5000')

        # Row 2: External URL
        row2 = tk.Frame(self.input_frame, bg=COLORS['bg'])
        row2.pack(fill='x', pady=5)

        tk.Label(row2, text="External URL:", bg=COLORS['bg'], fg=COLORS['fg'], font=('Arial', 10, 'bold')).pack(side='left', padx=(0, 5))
        self.url_entry = tk.Entry(row2, bg=COLORS['entry_bg'], fg=COLORS['fg'], insertbackground=COLORS['fg'], relief='flat', font=('Arial', 10))
        self.url_entry.pack(side='left', fill='x', expand=True, padx=5, ipady=5)
        self.url_entry.insert(0, 'http://127.0.0.1:8003/api/hl7/receive')

        # Row 3: Buttons
        button_frame = tk.Frame(self.input_frame, bg=COLORS['bg'])
        button_frame.pack(pady=10)

        self.start_button = tk.Button(button_frame, text="▶ Start Server", command=self.start_server,
                                      bg=COLORS['success'], fg='#000000', font=('Arial', 10, 'bold'),
                                      relief='flat', padx=20, pady=8, cursor='hand2')
        self.start_button.pack(side='left', padx=5)
        self.start_button.bind('<Enter>', lambda e: self.start_button.config(bg='#94e2d5'))
        self.start_button.bind('<Leave>', lambda e: self.start_button.config(bg=COLORS['success']))

        self.stop_button = tk.Button(button_frame, text="■ Stop Server", command=self.stop_server,
                                     bg=COLORS['error'], fg='#000000', font=('Arial', 10, 'bold'),
                                     relief='flat', padx=20, pady=8, cursor='hand2', state='disabled')
        self.stop_button.pack(side='left', padx=5)
        self.stop_button.bind('<Enter>', lambda e: self.stop_button.config(bg='#eba0ac') if self.server_running else None)
        self.stop_button.bind('<Leave>', lambda e: self.stop_button.config(bg=COLORS['error']) if self.server_running else None)

        # Text display areas
        self.received_frame = self.create_frame("Received Data")
        self.parsed_frame = self.create_frame("Formatted Data to Send")
        self.sent_frame = self.create_frame("Response from External URL")

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

        text_widget = tk.Text(frame, wrap=tk.WORD, height=10,
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
        widget.delete(1.0, tk.END)
        widget.insert(tk.END, content)
        widget.config(state=tk.DISABLED)

    def start_server(self):
        if self.server_running:
            messagebox.showinfo("Server Running", "Server is already running.")
            return

        ip = self.ip_entry.get()
        url = self.url_entry.get()
        try:
            port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Port", "Port must be an integer.")
            return

        if not url.startswith("http"):
            messagebox.showerror("Invalid URL", "Please enter a valid HTTP/HTTPS URL.")
            return

        self.server_running = True
        self.external_url = url
        self.connection_counter = 0

        # Update UI
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.status_label.config(text=f"● Online - {ip}:{port}", fg=COLORS['success'])

        threading.Thread(target=self.run_server, args=(ip, port), daemon=True).start()
        self.update_text(self.received_frame, f"Listening on {ip}:{port}...\n")

    def stop_server(self):
        if not self.server_running:
            return

        self.server_running = False

        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        # Update UI
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
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.status_label.config(text="● Offline", fg=COLORS['error'])
            return

        while self.server_running:
            try:
                self.server_socket.settimeout(1.0)
                client_socket, addr = self.server_socket.accept()
                self.connection_counter += 1
                self.connection_count.config(text=f"Connections: {self.connection_counter}")
                threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()
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
                display_msg = f"From {addr}:\n{received_data}"
                self.update_text(self.received_frame, display_msg)

                # Wrap the received string into a JSON object
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

                # Send to external API
                try:
                    headers = {'Content-Type': 'application/json'}
                    response = requests.post(self.external_url, json=payload, headers=headers)
                    result = f"Status Code: {response.status_code}\nResponse:\n{response.text}"
                except Exception as e:
                    result = f"Failed to send data:\n{str(e)}"

                self.update_text(self.sent_frame, result)

            except Exception as e:
                self.update_text(self.received_frame, f"Client error: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
