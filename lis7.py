import tkinter as tk
from tkinter import messagebox
import socket
import threading
import requests
import datetime


class XL180LabInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("XL-180 Lab Interface")

        # UI Components
        self.frame1 = tk.Frame(root)
        self.frame2 = tk.Frame(root)
        self.frame3 = tk.Frame(root)
        self.frame4 = tk.Frame(root)

        # Frame 1 - IP, Port, URL
        tk.Label(self.frame1, text="IP Address:").grid(row=0, column=0)
        tk.Label(self.frame1, text="Port:").grid(row=1, column=0)
        tk.Label(self.frame1, text="URL:").grid(row=2, column=0)

        self.ip_entry = tk.Entry(self.frame1)
        self.port_entry = tk.Entry(self.frame1)
        self.url_entry = tk.Entry(self.frame1)

        self.ip_entry.grid(row=0, column=1)
        self.port_entry.grid(row=1, column=1)
        self.url_entry.grid(row=2, column=1)

        self.save_button = tk.Button(self.frame1, text="Save & Start Listening", command=self.start_listening)
        self.save_button.grid(row=3, columnspan=2, pady=5)

        # Frame 2 - Connection Status
        self.connection_status = tk.Label(self.frame2, text="Not Connected", fg="red")
        self.connection_status.pack()

        # Frame 3 - Received Data
        tk.Label(self.frame3, text="Received Data:").pack()
        self.received_data = tk.Text(self.frame3, height=10)
        self.received_data.pack()

        # Frame 4 - Sent Data and Response
        tk.Label(self.frame4, text="Sent Data & Response:").pack()
        self.sent_data = tk.Text(self.frame4, height=10)
        self.sent_data.pack()

        # Layout
        self.frame1.grid(row=0, column=0, padx=10, pady=10)
        self.frame2.grid(row=0, column=1, padx=10, pady=10)
        self.frame3.grid(row=1, column=0, padx=10, pady=10)
        self.frame4.grid(row=1, column=1, padx=10, pady=10)

        # Log file
        self.log_file = "xl180_log.txt"

    def log_message(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        with open(self.log_file, 'a') as f:
            f.write(log_entry + "\n")

    def start_listening(self):
        ip = self.ip_entry.get()
        port = int(self.port_entry.get())
        self.url = self.url_entry.get()

        if not ip or not port or not self.url:
            messagebox.showerror("Input Error", "Please provide IP, Port, and URL.")
            return

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.server.bind((ip, port))
            self.server.listen(5)
            self.connection_status.config(text="Connected and Listening", fg="green")
            self.log_message(f"Server started and listening on {ip}:{port}")
            threading.Thread(target=self.accept_connections, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Server Error", f"Failed to bind: {e}")
            self.connection_status.config(text="Connection Failed", fg="red")

    def accept_connections(self):
        while True:
            client_socket, address = self.server.accept()
            self.log_message(f"Accepted connection from {address}")
            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()

    def handle_client(self, client_socket):
        with client_socket:
            while True:
                try:
                    data = client_socket.recv(1024)
                    if data:
                        self.log_message(f"Raw Data (Hex): {data.hex()}")

                        # Handshake logic: if ENQ (0x05), send ACK (0x06)
                        if b"\x05" in data:
                            self.log_message("ENQ received. Sending ACK.")
                            client_socket.send(b"\x06")

                        decoded_data = data.decode(errors='ignore')
                        self.received_data.insert(tk.END, f"{decoded_data}\n")

                        try:
                            response = requests.post(self.url, json={"data": decoded_data})
                            self.log_message(f"Data sent to URL with status: {response.status_code}")
                            self.sent_data.insert(tk.END, f"Sent: {decoded_data}\nStatus: {response.status_code} - {response.text}\n")
                        except Exception as e:
                            self.log_message(f"Failed to send to URL: {e}")
                            self.sent_data.insert(tk.END, f"Failed to send: {e}\n")
                except Exception as e:
                    self.log_message(f"Error handling client: {e}")
                    break


root = tk.Tk()
app = XL180LabInterface(root)
root.mainloop()
