import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import socket
import threading
import requests
import json
import os
import sys
import ftplib
import struct
import re
import subprocess
from datetime import datetime
from pathlib import Path

# Absolute paths — always relative to this script file
_SCRIPT_DIR = Path(__file__).resolve().parent
SAVE_DIR    = str(_SCRIPT_DIR / 'logs')
ECG_DIR     = str(_SCRIPT_DIR / 'ecg_received')
SCP_PARSER  = str(_SCRIPT_DIR / 'scp_parser.py')

# Create folders immediately on startup
Path(SAVE_DIR).mkdir(parents=True, exist_ok=True)
Path(ECG_DIR).mkdir(parents=True, exist_ok=True)

# ── Color scheme (matching original liscom.py) ────────────────────────────────
COLORS = {
    'bg':           '#1e1e2e',
    'fg':           '#cdd6f4',
    'accent':       '#89b4fa',
    'success':      '#a6e3a1',
    'error':        '#f38ba8',
    'warning':      '#fab387',
    'panel':        '#313244',
    'button':       '#45475a',
    'button_hover': '#585b70',
    'entry_bg':     '#181825',
    'label_frame':  '#313244',
    'ecg_line':     '#a6e3a1',
    'tab_active':   '#89b4fa',
}


# ══════════════════════════════════════════════════════════════════════════════
# ECG Parser  —  Edan SE-1200 .dat / .ecg file decoder
# ══════════════════════════════════════════════════════════════════════════════

class EdanECGParser:
    """
    Parses ECG files sent by Edan SE-1200 via FTP.
    Edan uses a proprietary binary format (.dat) with an XML/text header.
    Falls back to raw hex dump if format is unknown.
    """

    LEADS = ["I","II","III","aVR","aVL","aVF","V1","V2","V3","V4","V5","V6"]

    def parse(self, filepath: str) -> dict:
        result = {
            "filename":   os.path.basename(filepath),
            "timestamp":  datetime.now().isoformat(),
            "patient":    {},
            "leads":      {},
            "raw_hex":    "",
            "hl7":        "",
            "format":     "unknown",
        }

        with open(filepath, 'rb') as f:
            raw = f.read()

        result["raw_hex"] = raw[:64].hex(' ')

        # ── Try XML/text header (Edan embeds XML at start of .dat) ───────────
        try:
            text = raw.decode('utf-8', errors='ignore')
            result["patient"] = self._extract_patient_xml(text)
            result["format"]  = "edan_dat"
        except Exception:
            pass

        # ── Try to extract waveform data (12 leads × int16 samples) ──────────
        try:
            result["leads"] = self._extract_waveform(raw)
        except Exception:
            pass

        # ── Build HL7 ORU^R01 message ─────────────────────────────────────────
        result["hl7"] = self._build_hl7(result)

        return result

    def _extract_patient_xml(self, text: str) -> dict:
        patient = {}
        fields = {
            "PatientID":   r"<PatientID[^>]*>([^<]+)</PatientID>",
            "PatientName": r"<PatientName[^>]*>([^<]+)</PatientName>",
            "PatientAge":  r"<PatientAge[^>]*>([^<]+)</PatientAge>",
            "PatientSex":  r"<PatientSex[^>]*>([^<]+)</PatientSex>",
            "StudyDate":   r"<StudyDate[^>]*>([^<]+)</StudyDate>",
            "StudyTime":   r"<StudyTime[^>]*>([^<]+)</StudyTime>",
            "DeviceID":    r"<DeviceID[^>]*>([^<]+)</DeviceID>",
        }
        for key, pattern in fields.items():
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                patient[key] = m.group(1).strip()
        return patient

    def _extract_waveform(self, raw: bytes) -> dict:
        """
        Edan .dat files contain waveform data after the XML header.
        Each sample is a signed 16-bit little-endian integer.
        12 leads are interleaved: [I, II, III, aVR, aVL, aVF, V1..V6]
        """
        leads = {lead: [] for lead in self.LEADS}
        # Find waveform start — skip past XML (after last '>')
        xml_end = raw.rfind(b'>') + 1
        if xml_end < 100:
            xml_end = 0
        waveform = raw[xml_end:]
        num_samples = len(waveform) // (12 * 2)
        for i in range(num_samples):
            for j, lead in enumerate(self.LEADS):
                offset = (i * 12 + j) * 2
                if offset + 2 <= len(waveform):
                    val = struct.unpack_from('<h', waveform, offset)[0]
                    leads[lead].append(val * 0.00488)  # convert to mV
        return leads

    def _build_hl7(self, result: dict) -> str:
        """Build HL7 v2.x ORU^R01 message for LIS/HIS integration."""
        now     = datetime.now().strftime('%Y%m%d%H%M%S')
        patient = result.get("patient", {})
        pid     = patient.get("PatientID",   "UNKNOWN")
        name    = patient.get("PatientName", "UNKNOWN")
        age     = patient.get("PatientAge",  "")
        sex     = patient.get("PatientSex",  "")
        dt      = patient.get("StudyDate",   now[:8])
        tm      = patient.get("StudyTime",   now[8:])

        # Count leads with data
        leads_summary = ", ".join(
            f"{lead}:{len(v)}smp"
            for lead, v in result.get("leads", {}).items()
            if v
        ) or "No waveform data"

        hl7 = (
            f"MSH|^~\\&|EDAN_ECG|SE1200|LIS|HOSPITAL|{now}||ORU^R01|{now}|P|2.5\r"
            f"PID|1||{pid}^^^HOSP||{name}||{age}|{sex}\r"
            f"OBR|1||{dt}{tm}|93000^Electrocardiogram^CPT|||{dt}{tm}\r"
            f"OBX|1|ST|93000^ECG Report^CPT||{leads_summary}||||||F\r"
            f"OBX|2|ST|FILE^Source File^LOCAL||{result['filename']}||||||F\r"
        )
        return hl7

    def save_hl7(self, hl7: str, base_path: str) -> str:
        path = base_path.replace('.dat', '.hl7').replace('.ecg', '.hl7') + '.hl7'
        with open(path, 'w') as f:
            f.write(hl7)
        return path


# ══════════════════════════════════════════════════════════════════════════════
# Embedded FTP Server  —  receives files from Edan SE-1200
# ══════════════════════════════════════════════════════════════════════════════

class EmbeddedFTPHandler:
    """
    Minimal FTP server that accepts files from the Edan SE-1200.
    Uses Python's built-in socket — no vsftpd needed.
    Credentials: EDANDAT / (blank password)
    """

    def __init__(self, host='0.0.0.0', port=21, save_dir=ECG_DIR,
                 on_file_received=None, log_callback=None):
        self.host             = host
        self.port             = port
        self.save_dir         = Path(save_dir)
        self.on_file_received = on_file_received   # callback(filepath)
        self.log              = log_callback or print
        self.running          = False
        self.server_sock      = None
        self.save_dir.mkdir(exist_ok=True)

    def start(self):
        self.running = True
        threading.Thread(target=self._serve, daemon=True).start()

    def stop(self):
        self.running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass

    def _serve(self):
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((self.host, self.port))
            self.server_sock.listen(5)
            self.log(f"FTP server listening on {self.host}:{self.port}")
            while self.running:
                try:
                    self.server_sock.settimeout(1.0)
                    conn, addr = self.server_sock.accept()
                    self.log(f"FTP connection from {addr[0]}")
                    threading.Thread(
                        target=self._handle_client,
                        args=(conn, addr),
                        daemon=True
                    ).start()
                except socket.timeout:
                    continue
        except PermissionError:
            self.log("ERROR: Port 21 requires root. Run: sudo python3 liscom_ecg.py")
            self.log("  OR use port 2121 and set machine FTP port to 2121")
        except Exception as e:
            self.log(f"FTP server error: {e}")

    def _handle_client(self, conn, addr):
        """Handle one FTP session (simplified for Edan SE-1200 STOR command)."""
        filepath   = None
        data_sock  = None
        pasv_sock  = None
        logged_in  = False
        username   = ""

        def send(msg):
            conn.sendall((msg + '\r\n').encode())

        try:
            send("220 Edan ECG FTP Server Ready")

            while True:
                try:
                    line = conn.recv(1024).decode('utf-8', errors='ignore').strip()
                except Exception:
                    break
                if not line:
                    break

                cmd  = line.split(' ')[0].upper()
                args = line[len(cmd):].strip()
                self.log(f"FTP CMD: {line}")

                if cmd == 'USER':
                    username = args
                    send("331 Password required")

                elif cmd == 'PASS':
                    # Accept any password for EDANDAT
                    if username.upper() in ('EDANDAT', 'ANONYMOUS', ''):
                        logged_in = True
                        send("230 Login successful")
                    else:
                        send("530 Login incorrect")

                elif cmd == 'SYST':
                    send("215 UNIX Type: L8")

                elif cmd == 'TYPE':
                    send("200 Type set")

                elif cmd == 'PWD':
                    send('257 "/" is current directory')

                elif cmd == 'CWD':
                    send("250 Directory changed")

                elif cmd == 'MKD':
                    send('257 Directory created')

                elif cmd == 'PASV':
                    # Open passive data port
                    pasv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    pasv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    pasv_sock.bind(('0.0.0.0', 0))
                    pasv_sock.listen(1)
                    pasv_port = pasv_sock.getsockname()[1]
                    # Get local IP
                    local_ip  = socket.gethostbyname(socket.gethostname())
                    ip_parts  = local_ip.replace('.', ',')
                    p1, p2    = pasv_port >> 8, pasv_port & 0xFF
                    send(f"227 Entering Passive Mode ({ip_parts},{p1},{p2})")

                elif cmd == 'STOR':
                    if not logged_in:
                        send("530 Not logged in")
                        continue
                    filename = os.path.basename(args)
                    filepath = self.save_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    send("150 Opening data connection")

                    # Accept data connection
                    if pasv_sock:
                        pasv_sock.settimeout(10)
                        try:
                            data_sock, _ = pasv_sock.accept()
                            file_data = b""
                            while True:
                                chunk = data_sock.recv(65536)
                                if not chunk:
                                    break
                                file_data += chunk
                            data_sock.close()
                            pasv_sock.close()
                            pasv_sock = None

                            with open(filepath, 'wb') as f:
                                f.write(file_data)

                            self.log(f"ECG FILE RECEIVED: {filepath} ({len(file_data)} bytes)")
                            send("226 Transfer complete")

                            # Trigger callback
                            if self.on_file_received:
                                threading.Thread(
                                    target=self.on_file_received,
                                    args=(str(filepath),),
                                    daemon=True
                                ).start()
                        except socket.timeout:
                            send("425 Data connection timeout")
                    else:
                        send("425 Use PASV first")

                elif cmd == 'QUIT':
                    send("221 Goodbye")
                    break

                else:
                    send(f"500 Unknown command: {cmd}")

        except Exception as e:
            self.log(f"FTP client error: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
            if pasv_sock:
                try:
                    pasv_sock.close()
                except Exception:
                    pass


# ══════════════════════════════════════════════════════════════════════════════
# Main Application  —  extends original liscom.py with ECG tab
# ══════════════════════════════════════════════════════════════════════════════

class SerialTcpApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TS-LISA  +  ECG")
        self.root.configure(bg=COLORS['bg'])
        self.root.geometry("1200x900")

        self.serial_port       = None
        self.server_socket     = None
        self.running           = False
        self.connection_counter = 0
        self.ftp_server        = None
        self.ecg_parser        = EdanECGParser()

        # folders already created at module load via Path.mkdir above

        self.setup_styles()

        # ── Notebook (tabs) ───────────────────────────────────────────────────
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Tab 1 — original LIS
        self.lis_tab = tk.Frame(self.notebook, bg=COLORS['bg'])
        self.notebook.add(self.lis_tab, text="  📡 LIS Listener  ")

        # Tab 2 — ECG
        self.ecg_tab = tk.Frame(self.notebook, bg=COLORS['bg'])
        self.notebook.add(self.ecg_tab, text="  🫀 ECG Receiver  ")

        # Build both tabs
        self._build_lis_tab()
        self._build_ecg_tab()

        # Status bar (shared)
        self.create_status_bar()

        self.refresh_ports()
        self.toggle_mode()

    # ══════════════════════════════════════════════════════════════════════════
    # LIS TAB  (original liscom.py UI — unchanged)
    # ══════════════════════════════════════════════════════════════════════════

    def _build_lis_tab(self):
        self.create_mode_selector()
        self.create_serial_config()
        self.create_tcp_config()
        self.create_api_config()
        self.create_control_buttons()
        self.received_text = self.create_frame("Received Data",       parent=self.lis_tab)
        self.sent_text     = self.create_frame("Formatted Data to Send", parent=self.lis_tab)
        self.response_text = self.create_frame("API Response",        parent=self.lis_tab)

    # ══════════════════════════════════════════════════════════════════════════
    # ECG TAB
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ecg_tab(self):
        tab = self.ecg_tab

        # ── Config row ────────────────────────────────────────────────────────
        cfg = tk.Frame(tab, bg=COLORS['bg'])
        cfg.pack(fill='x', padx=10, pady=10)

        # FTP port
        tk.Label(cfg, text="FTP Port:", bg=COLORS['bg'], fg=COLORS['fg'],
                 font=('Arial', 10, 'bold')).pack(side='left', padx=(0, 5))
        self.ftp_port_entry = tk.Entry(cfg, width=6, bg=COLORS['entry_bg'], fg=COLORS['fg'],
                                       insertbackground=COLORS['fg'], relief='flat',
                                       font=('Arial', 10))
        self.ftp_port_entry.pack(side='left', padx=5, ipady=5)
        self.ftp_port_entry.insert(0, '21')

        tk.Label(cfg, text="  Save to:", bg=COLORS['bg'], fg=COLORS['fg'],
                 font=('Arial', 10, 'bold')).pack(side='left', padx=(10, 5))
        self.ecg_save_entry = tk.Entry(cfg, width=20, bg=COLORS['entry_bg'], fg=COLORS['fg'],
                                       insertbackground=COLORS['fg'], relief='flat',
                                       font=('Arial', 10))
        self.ecg_save_entry.pack(side='left', padx=5, ipady=5)
        self.ecg_save_entry.insert(0, ECG_DIR)

        # LIS API URL for forwarding
        tk.Label(cfg, text="  LIS API:", bg=COLORS['bg'], fg=COLORS['fg'],
                 font=('Arial', 10, 'bold')).pack(side='left', padx=(10, 5))
        self.ecg_api_entry = tk.Entry(cfg, width=35, bg=COLORS['entry_bg'], fg=COLORS['fg'],
                                      insertbackground=COLORS['fg'], relief='flat',
                                      font=('Arial', 10))
        self.ecg_api_entry.pack(side='left', padx=5, ipady=5, fill='x', expand=True)
        self.ecg_api_entry.insert(0, 'http://127.0.0.1:8003/api/ecg/receive')

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = tk.Frame(tab, bg=COLORS['bg'])
        btn_row.pack(pady=8)

        self.ecg_start_btn = tk.Button(
            btn_row, text="▶ Start ECG Receiver",
            command=self.start_ecg_receiver,
            bg=COLORS['success'], fg='#000000',
            font=('Arial', 10, 'bold'), relief='flat',
            padx=20, pady=8, cursor='hand2'
        )
        self.ecg_start_btn.pack(side='left', padx=5)
        self.ecg_start_btn.bind('<Enter>', lambda e: self.ecg_start_btn.config(bg='#94e2d5'))
        self.ecg_start_btn.bind('<Leave>', lambda e: self.ecg_start_btn.config(bg=COLORS['success']))

        self.ecg_stop_btn = tk.Button(
            btn_row, text="■ Stop ECG Receiver",
            command=self.stop_ecg_receiver,
            bg=COLORS['error'], fg='#000000',
            font=('Arial', 10, 'bold'), relief='flat',
            padx=20, pady=8, cursor='hand2', state='disabled'
        )
        self.ecg_stop_btn.pack(side='left', padx=5)

        self.ecg_status_label = tk.Label(
            btn_row, text="● Offline",
            bg=COLORS['bg'], fg=COLORS['error'],
            font=('Arial', 10, 'bold')
        )
        self.ecg_status_label.pack(side='left', padx=15)

        # ── Machine info row ──────────────────────────────────────────────────
        info_row = tk.Frame(tab, bg=COLORS['panel'])
        info_row.pack(fill='x', padx=10, pady=2)
        tk.Label(info_row,
                 text="Edan SE-1200 Express  |  FTP mode  |  "
                      "Machine IP: 192.168.0.170  |  "
                      "Credentials: EDANDAT / (blank)",
                 bg=COLORS['panel'], fg=COLORS['warning'],
                 font=('Arial', 9)).pack(side='left', padx=10, pady=4)

        # ── Text panels ───────────────────────────────────────────────────────
        self.ecg_log_text    = self.create_frame("ECG Transfer Log",  parent=tab)
        self.ecg_parsed_text = self.create_frame("Parsed ECG Data & Patient Info", parent=tab)
        self.ecg_hl7_text    = self.create_frame("HL7 Message (forwarded to LIS)", parent=tab)

    # ── ECG Receiver controls ─────────────────────────────────────────────────

    def start_ecg_receiver(self):
        try:
            port = int(self.ftp_port_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Port", "FTP port must be a number.")
            return

        save_dir = self.ecg_save_entry.get() or ECG_DIR

        self.ftp_server = EmbeddedFTPHandler(
            host='0.0.0.0',
            port=port,
            save_dir=save_dir,
            on_file_received=self.on_ecg_file_received,
            log_callback=lambda msg: self.root.after(
                0, self.update_text, self.ecg_log_text, msg
            ),
        )
        self.ftp_server.start()

        self.ecg_start_btn.config(state='disabled')
        self.ecg_stop_btn.config(state='normal')
        self.ecg_status_label.config(
            text=f"● Listening on FTP :{port}", fg=COLORS['success']
        )
        self.update_text(self.ecg_log_text,
                         f"[{_now()}] ECG FTP receiver started on port {port}")
        self.update_text(self.ecg_log_text,
                         f"[{_now()}] Saving files to: {save_dir}")
        self.update_text(self.ecg_log_text,
                         f"[{_now()}] Waiting for Edan SE-1200 to send ECG data ...")

    def stop_ecg_receiver(self):
        if self.ftp_server:
            self.ftp_server.stop()
            self.ftp_server = None
        self.ecg_start_btn.config(state='normal')
        self.ecg_stop_btn.config(state='disabled')
        self.ecg_status_label.config(text="● Offline", fg=COLORS['error'])
        self.update_text(self.ecg_log_text, f"[{_now()}] ECG receiver stopped.")

    def on_ecg_file_received(self, filepath: str):
        """Called in background thread when FTP upload completes."""
        self.root.after(0, self._process_ecg_file, filepath)

    def _process_ecg_file(self, filepath: str):
        filename = os.path.basename(filepath)
        self.update_text(self.ecg_log_text, f"[{_now()}] ✔ File received: {filename}")

        parsed   = {}
        log_text = ""
        hl7      = ""

        # ── Step 1: Run scp_parser.py --json ──────────────────────────────────
        try:
            if os.path.exists(SCP_PARSER):
                proc = subprocess.run(
                    [sys.executable, SCP_PARSER, filepath, '--json'],
                    capture_output=True, text=True, timeout=15
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    parsed = json.loads(proc.stdout.strip())
                    self.update_text(self.ecg_log_text,
                                     f"[{_now()}] ✔ SCP-ECG parsed successfully")
                else:
                    self.update_text(self.ecg_log_text,
                                     f"[{_now()}] ⚠ Parser stderr: {proc.stderr.strip()[:100]}")
            else:
                self.update_text(self.ecg_log_text,
                                 f"[{_now()}] ⚠ scp_parser.py not found at: {SCP_PARSER}")
        except Exception as e:
            self.update_text(self.ecg_log_text, f"[{_now()}] Parser error: {e}")

        # ── Step 2: Run scp_parser.py --log for human-readable text ──────────
        try:
            if os.path.exists(SCP_PARSER):
                proc2 = subprocess.run(
                    [sys.executable, SCP_PARSER, filepath, '--log'],
                    capture_output=True, text=True, timeout=15
                )
                log_text = proc2.stdout if proc2.returncode == 0 else ""
        except Exception:
            pass
        if not log_text:
            log_text = (
                f"ECG File : {filename}\n"
                f"Size     : {os.path.getsize(filepath):,} bytes\n"
                f"Received : {datetime.now().isoformat()}\n"
            )

        # ── Step 3: Save .log file to logs/ folder ────────────────────────────
        try:
            stamp    = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_path = os.path.join(SAVE_DIR,
                                    os.path.splitext(filename)[0] + f'_{stamp}.log')
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(log_text)
            self.update_text(self.ecg_log_text,
                             f"[{_now()}] ✔ Log saved  → {os.path.basename(log_path)}")
        except Exception as e:
            self.update_text(self.ecg_log_text, f"[{_now()}] Log save error: {e}")

        # ── Step 4: Build HL7 message ─────────────────────────────────────────
        try:
            hl7 = self._build_hl7(parsed, filename)
            hl7_path = filepath + '.hl7'
            with open(hl7_path, 'w', encoding='utf-8') as f:
                f.write(hl7)
            self.update_text(self.ecg_log_text,
                             f"[{_now()}] ✔ HL7 saved  → {os.path.basename(hl7_path)}")
        except Exception as e:
            self.update_text(self.ecg_log_text, f"[{_now()}] HL7 error: {e}")

        # ── Step 5: Update UI panels ──────────────────────────────────────────
        self.update_text(self.ecg_parsed_text, log_text)
        if hl7:
            self.update_text(self.ecg_hl7_text, hl7)

        # ── Step 6: POST to Laravel in background thread ──────────────────────
        threading.Thread(
            target=self._forward_to_lis,
            args=(parsed, hl7, filename, filepath),
            daemon=True
        ).start()

    def _build_hl7(self, parsed: dict, filename: str) -> str:
        now     = datetime.now().strftime('%Y%m%d%H%M%S')
        p       = parsed.get('patient', {})
        meas    = parsed.get('measurements', {})
        interp  = parsed.get('interpretation', {})
        diag    = parsed.get('diagnosis', {})
        pid     = p.get('id')   or 'UNKNOWN'
        name    = p.get('name') or 'UNKNOWN'
        age     = p.get('age')  or ''
        sex     = p.get('sex')  or ''
        hr_obj  = meas.get('heart_rate', {})
        hr      = hr_obj.get('value', '') if isinstance(hr_obj, dict) else meas.get('heart_rate_bpm', '')
        summary = (interp.get('summary') or '')[:80]
        auto_dx = ', '.join(diag.get('auto_diagnosis', [])) if isinstance(diag.get('auto_diagnosis'), list) else ''
        return (
            f"MSH|^~\\&|EDAN_ECG|SE1200|LIS|HOSPITAL|{now}||ORU^R01|{now}|P|2.5\r"
            f"PID|1||{pid}^^^HOSP||{name}||{age}|{sex}\r"
            f"OBR|1||{now}|93000^Electrocardiogram^CPT|||{now}\r"
            f"OBX|1|ST|93000^ECG^CPT||{summary}||||||F\r"
            f"OBX|2|NM|HR^HeartRate^LOCAL||{hr}|bpm|||||F\r"
            f"OBX|3|ST|DX^AutoDiagnosis^LOCAL||{auto_dx}||||||F\r"
            f"OBX|4|ST|FILE^SourceFile^LOCAL||{filename}||||||F\r"
        )

    def _forward_to_lis(self, parsed: dict, hl7: str, filename: str, filepath: str):
        # Runs in background thread — safe to call requests here
        api_url = self.ecg_api_entry.get().strip()
        if not api_url.startswith('http'):
            self.root.after(0, self.update_text, self.ecg_log_text,
                            f"[{_now()}] ⚠ No API URL — skipping DB save")
            return

        try:
            p = parsed.get('patient', {})
            payload = {
                "source":    "edan_se1200",
                "device_no": "1871844",
                "filename":  filename,
                "timestamp": datetime.now().isoformat(),
                "hl7":       hl7,
                "parsed":    parsed,
                "patient": {
                    "id":                  p.get('id'),
                    "name":                p.get('name'),
                    "first_name":          p.get('first_name'),
                    "last_name":           p.get('last_name'),
                    "dob":                 p.get('dob'),
                    "age":                 p.get('age'),
                    "sex":                 p.get('sex'),
                    "weight":              p.get('weight'),
                    "height":              p.get('height'),
                    "room":                p.get('room'),
                    "hospital":            p.get('hospital'),
                    "department":          p.get('department'),
                    "referring_physician": p.get('referring_physician'),
                    "diagnosis_doctor":    p.get('diagnosis_doctor'),
                    "technician":          p.get('technician'),
                },
                "leads": parsed.get('leads', []),
            }

            self.root.after(0, self.update_text, self.ecg_log_text,
                            f"[{_now()}] → POSTing to: {api_url}")

            resp = requests.post(
                api_url, json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            try:
                rdata     = resp.json()
                record_id = rdata.get('data', {}).get('id', '') if resp.status_code in (200, 201) else ''
                msg = (f"[{_now()}] ✔ DB saved  id={record_id}"
                       if resp.status_code in (200, 201)
                       else f"[{_now()}] ✘ API {resp.status_code}: {resp.text[:120]}")
            except Exception:
                msg = f"[{_now()}] API {resp.status_code}: {resp.text[:80]}"

            self.root.after(0, self.update_text, self.ecg_log_text, msg)

            # Save JSON copy to logs/
            try:
                stamp     = datetime.now().strftime('%Y%m%d_%H%M%S')
                json_path = os.path.join(SAVE_DIR,
                                         os.path.splitext(filename)[0] + f'_{stamp}.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, indent=2, default=str)
                self.root.after(0, self.update_text, self.ecg_log_text,
                                f"[{_now()}] ✔ JSON saved → {os.path.basename(json_path)}")
            except Exception:
                pass

        except requests.exceptions.ConnectionError:
            self.root.after(0, self.update_text, self.ecg_log_text,
                            f"[{_now()}] ✘ Cannot reach {api_url} — is Laravel running?")
        except Exception as e:
            self.root.after(0, self.update_text, self.ecg_log_text,
                            f"[{_now()}] ✘ API error: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # Original LIS tab methods (unchanged from liscom.py)
    # ══════════════════════════════════════════════════════════════════════════

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook',        background=COLORS['bg'],  borderwidth=0)
        style.configure('TNotebook.Tab',    background=COLORS['panel'], foreground=COLORS['fg'],
                        padding=[12, 6],    font=('Arial', 10, 'bold'))
        style.map('TNotebook.Tab',
                  background=[('selected', COLORS['accent'])],
                  foreground=[('selected', '#000000')])

    def create_status_bar(self):
        self.status_bar = tk.Frame(self.root, bg=COLORS['panel'], relief='flat', bd=0)
        self.status_bar.pack(side='bottom', fill='x')
        self.status_label = tk.Label(self.status_bar, text="● Offline",
                                     bg=COLORS['panel'], fg=COLORS['error'],
                                     font=('Arial', 9, 'bold'), anchor='w')
        self.status_label.pack(side='left', padx=10, pady=5)
        self.connection_count = tk.Label(self.status_bar, text="Connections: 0",
                                         bg=COLORS['panel'], fg=COLORS['fg'],
                                         font=('Arial', 9), anchor='e')
        self.connection_count.pack(side='right', padx=10, pady=5)

    def create_mode_selector(self):
        self.mode_frame = tk.Frame(self.lis_tab, bg=COLORS['bg'])
        self.mode_frame.pack(pady=10, padx=10, fill='x')
        tk.Label(self.mode_frame, text="Mode:", bg=COLORS['bg'],
                 fg=COLORS['accent'], font=('Arial', 11, 'bold')).pack(side='left', padx=(0, 10))
        self.mode_var = tk.StringVar(value="serial")
        tk.Radiobutton(self.mode_frame, text="📡 Serial Port", variable=self.mode_var,
                       value="serial", command=self.toggle_mode,
                       bg=COLORS['bg'], fg=COLORS['fg'], selectcolor=COLORS['panel'],
                       font=('Arial', 10), activebackground=COLORS['bg'],
                       activeforeground=COLORS['accent'], cursor='hand2').pack(side='left', padx=5)
        tk.Radiobutton(self.mode_frame, text="🌐 TCP Socket", variable=self.mode_var,
                       value="tcp", command=self.toggle_mode,
                       bg=COLORS['bg'], fg=COLORS['fg'], selectcolor=COLORS['panel'],
                       font=('Arial', 10), activebackground=COLORS['bg'],
                       activeforeground=COLORS['accent'], cursor='hand2').pack(side='left', padx=5)

    def create_serial_config(self):
        self.serial_frame = tk.Frame(self.lis_tab, bg=COLORS['bg'])
        self.serial_frame.pack(pady=5, padx=10, fill='x')
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
        self.tcp_frame = tk.Frame(self.lis_tab, bg=COLORS['bg'])
        self.tcp_frame.pack(pady=5, padx=10, fill='x')
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
        api_frame = tk.Frame(self.lis_tab, bg=COLORS['bg'])
        api_frame.pack(pady=5, padx=10, fill='x')
        tk.Label(api_frame, text="API URL:", bg=COLORS['bg'], fg=COLORS['fg'],
                 font=('Arial', 10, 'bold')).pack(side='left', padx=(0, 5))
        self.url_entry = tk.Entry(api_frame, bg=COLORS['entry_bg'], fg=COLORS['fg'],
                                  insertbackground=COLORS['fg'], relief='flat', font=('Arial', 10))
        self.url_entry.pack(side='left', fill='x', expand=True, padx=5, ipady=5)
        self.url_entry.insert(0, 'http://127.0.0.1:8003/api/hl7/receive')

    def create_control_buttons(self):
        button_frame = tk.Frame(self.lis_tab, bg=COLORS['bg'])
        button_frame.pack(pady=15)
        self.start_button = tk.Button(button_frame, text="▶ Start Listening",
                                      command=self.start_listening,
                                      bg=COLORS['success'], fg='#000000',
                                      font=('Arial', 10, 'bold'), relief='flat',
                                      padx=20, pady=8, cursor='hand2')
        self.start_button.pack(side='left', padx=5)
        self.start_button.bind('<Enter>', lambda e: self.start_button.config(bg='#94e2d5'))
        self.start_button.bind('<Leave>', lambda e: self.start_button.config(bg=COLORS['success']))
        self.stop_button = tk.Button(button_frame, text="■ Stop Listening",
                                     command=self.stop_listening,
                                     bg=COLORS['error'], fg='#000000',
                                     font=('Arial', 10, 'bold'), relief='flat',
                                     padx=20, pady=8, cursor='hand2', state='disabled')
        self.stop_button.pack(side='left', padx=5)

    def create_frame(self, title, parent=None):
        if parent is None:
            parent = self.root
        container = tk.Frame(parent, bg=COLORS['bg'])
        container.pack(fill="both", expand=True, padx=10, pady=5)
        frame = tk.LabelFrame(container, text=title, padx=10, pady=10,
                              bg=COLORS['label_frame'], fg=COLORS['accent'],
                              font=('Arial', 10, 'bold'), relief='flat', bd=2)
        frame.pack(fill="both", expand=True)
        btn_frame = tk.Frame(frame, bg=COLORS['label_frame'])
        btn_frame.pack(fill='x', pady=(0, 5))
        text_widget = tk.Text(frame, wrap=tk.WORD, height=7,
                              bg=COLORS['entry_bg'], fg=COLORS['fg'],
                              insertbackground=COLORS['fg'], relief='flat',
                              font=('Consolas', 9), padx=10, pady=10,
                              state=tk.DISABLED)
        text_widget.pack(fill="both", expand=True)
        clear_btn = tk.Button(btn_frame, text="✕ Clear",
                              command=lambda tw=text_widget: self.clear_text(tw),
                              bg=COLORS['button'], fg=COLORS['fg'], font=('Arial', 8),
                              relief='flat', padx=10, pady=3, cursor='hand2')
        clear_btn.pack(side='right')
        clear_btn.bind('<Enter>', lambda e: clear_btn.config(bg=COLORS['button_hover']))
        clear_btn.bind('<Leave>', lambda e: clear_btn.config(bg=COLORS['button']))
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
        url  = self.url_entry.get()
        if not url.startswith("http"):
            messagebox.showerror("Invalid URL", "Please enter a valid HTTP/HTTPS URL.")
            return
        self.external_url       = url
        self.running            = True
        self.connection_counter = 0
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
        ip   = self.ip_entry.get()
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
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
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
                threading.Thread(target=self.handle_tcp_client,
                                 args=(client_socket, addr), daemon=True).start()
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
        json_data      = {"data": data}
        formatted_json = json.dumps(json_data, indent=2)
        self.update_text(self.sent_text, formatted_json)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename  = os.path.join(SAVE_DIR, f"sent_{timestamp}.json")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2)
        except Exception as e:
            print(f"Error saving file: {e}")
        try:
            headers  = {'Content-Type': 'application/json'}
            response = requests.post(self.external_url, json=json_data,
                                     headers=headers, timeout=5)
            result   = f"Status: {response.status_code}\n{response.text}"
            response_file = os.path.join(SAVE_DIR, f"response_{timestamp}.json")
            try:
                with open(response_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
            except Exception:
                pass
        except Exception as e:
            result = f"API Error: {str(e)}"
        self.update_text(self.response_text, result)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().strftime('%H:%M:%S')


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app  = SerialTcpApp(root)
    root.mainloop()
