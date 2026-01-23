import socket
import threading
import tkinter as tk
from tkinter import messagebox
import requests
import json
import os
from datetime import datetime


SAVE_DIR = 'sent_messages'


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Socket Listener and Forwarder")

        self.server_running = False
        os.makedirs(SAVE_DIR, exist_ok=True)

        # Input fields: IP, Port, External URL
        self.input_frame = tk.Frame(self.root)
        self.input_frame.pack(pady=10)

        tk.Label(self.input_frame, text="IP:").grid(row=0, column=0)
        self.ip_entry = tk.Entry(self.input_frame, width=15)
        self.ip_entry.grid(row=0, column=1, padx=5)
        self.ip_entry.insert(0, '127.0.0.1')

        tk.Label(self.input_frame, text="Port:").grid(row=0, column=2)
        self.port_entry = tk.Entry(self.input_frame, width=6)
        self.port_entry.grid(row=0, column=3, padx=5)
        self.port_entry.insert(0, '5000')

        tk.Label(self.input_frame, text="External URL:").grid(row=0, column=4)
        self.url_entry = tk.Entry(self.input_frame, width=40)
        self.url_entry.grid(row=0, column=5, padx=5)
        self.url_entry.insert(0, 'http://127.0.0.1:8003/api/hl7/receive')

        self.start_button = tk.Button(self.input_frame, text="Start Server", command=self.start_server)
        self.start_button.grid(row=0, column=6, padx=10)

        # Text display areas
        self.received_frame = self.create_frame("Received Data")
        self.parsed_frame = self.create_frame("Formatted Data to Send")
        self.sent_frame = self.create_frame("Response from External URL")

    def create_frame(self, title):
        frame = tk.LabelFrame(self.root, text=title, padx=10, pady=10)
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        text_widget = tk.Text(frame, wrap=tk.WORD, height=10)
        text_widget.pack(fill="both", expand=True)
        return text_widget

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
        threading.Thread(target=self.run_server, args=(ip, port), daemon=True).start()
        self.update_text(self.received_frame, f"Listening on {ip}:{port}...\n")

    def run_server(self, host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            try:
                server_socket.bind((host, port))
                server_socket.listen()
            except Exception as e:
                self.update_text(self.received_frame, f"Error binding socket: {str(e)}")
                return

            while True:
                client_socket, addr = server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()

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
