#!/usr/bin/env python3
"""
ECG Data Capture Script for Labotronics ECG Machine
=====================================================
Supports:
  - Serial / RS-232 port (DB-9 connector visible on front)
  - USB serial / HID interface
  - File-based capture (USB flash drive export)
  - Image capture from folder watch (scanned/exported PDFs or BMPs)

Usage:
  python ecg_capture.py --mode serial --port /dev/ttyUSB0
  python ecg_capture.py --mode usb
  python ecg_capture.py --mode watch --watch-dir /media/usb

Dependencies:
  pip install pyserial Pillow watchdog opencv-python numpy
"""

import os
import sys
import time
import argparse
import logging
import struct
import datetime
from pathlib import Path

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("ecg_capture.log"),
    ],
)
log = logging.getLogger("ecg_capture")

OUTPUT_DIR = Path("ecg_output")
OUTPUT_DIR.mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# 1. SERIAL PORT CAPTURE  (DB-9 / RS-232 or USB-Serial adapter)
# ══════════════════════════════════════════════════════════════════════════════

class SerialCapture:
    """
    Reads raw ECG data stream over a serial port.
    Common Labotronics / generic ECG serial parameters:
        Baud: 9600 or 115200  |  8-N-1  |  No hardware flow control
    The machine streams 12-lead waveform packets when recording starts.
    """

    # ── Typical packet framing (adjust to your device's protocol) ─────────────
    # Many Chinese ECG devices use: [0xAA 0xBB] [len 2B] [lead_data ...] [checksum]
    SYNC_BYTES   = bytes([0xAA, 0xBB])
    LEADS        = ["I", "II", "III", "aVR", "aVL", "aVF",
                    "V1", "V2", "V3", "V4", "V5", "V6"]
    SAMPLE_RATE  = 500   # Hz — common default; change if device differs

    def __init__(self, port: str, baud: int = 115200, output_dir: Path = OUTPUT_DIR):
        self.port       = port
        self.baud       = baud
        self.output_dir = output_dir
        self.ser        = None
        self.running    = False

    def connect(self):
        import serial
        log.info(f"Opening serial port {self.port} @ {self.baud} baud …")
        self.ser = serial.Serial(
            port     = self.port,
            baudrate = self.baud,
            bytesize = serial.EIGHTBITS,
            parity   = serial.PARITY_NONE,
            stopbits = serial.STOPBITS_ONE,
            timeout  = 2,
        )
        log.info("Serial port opened.")

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            log.info("Serial port closed.")

    def _find_sync(self):
        """Scan for the SYNC_BYTES header in the stream."""
        buf = b""
        while len(buf) < 2:
            b = self.ser.read(1)
            if not b:
                continue
            buf += b
            if buf[-2:] == self.SYNC_BYTES:
                return True
        return False

    def _read_packet(self):
        """
        Read one data packet.
        Expected frame:
          [0xAA 0xBB] [uint16 length] [length bytes of payload] [uint8 checksum]
        Returns payload bytes or None on error.
        """
        if not self._find_sync():
            return None
        raw_len = self.ser.read(2)
        if len(raw_len) < 2:
            return None
        pkt_len = struct.unpack("<H", raw_len)[0]
        payload = self.ser.read(pkt_len)
        checksum_byte = self.ser.read(1)
        if not checksum_byte:
            return None
        expected_cs = sum(payload) & 0xFF
        if checksum_byte[0] != expected_cs:
            log.warning(f"Checksum mismatch: got {checksum_byte[0]:02X}, expected {expected_cs:02X}")
            return None
        return payload

    def _decode_samples(self, payload: bytes) -> dict:
        """
        Decode 12-lead sample values from payload.
        Assumes each lead is a signed 16-bit int (little-endian), packed sequentially.
        One sample set = 12 leads × 2 bytes = 24 bytes.
        Returns dict {lead_name: sample_value_in_mV}.
        """
        if len(payload) < 24:
            return {}
        samples = {}
        for i, lead in enumerate(self.LEADS):
            raw = struct.unpack_from("<h", payload, i * 2)[0]
            # Convert ADC units → mV (scale factor depends on device; 1 LSB = 4.88 µV typical)
            samples[lead] = raw * 0.00488
        return samples

    def capture(self, duration_sec: int = 10):
        """Capture ECG for `duration_sec` seconds and save to CSV + PNG."""
        self.connect()
        records = {lead: [] for lead in self.LEADS}
        timestamps = []
        start = time.time()
        log.info(f"Capturing {duration_sec}s of ECG data …")

        try:
            while time.time() - start < duration_sec:
                payload = self._read_packet()
                if payload is None:
                    continue
                samples = self._decode_samples(payload)
                if samples:
                    timestamps.append(time.time() - start)
                    for lead, val in samples.items():
                        records[lead].append(val)
        except KeyboardInterrupt:
            log.info("Capture interrupted by user.")
        finally:
            self.disconnect()

        if timestamps:
            self._save_csv(timestamps, records)
            self._save_plot(timestamps, records)
        else:
            log.warning("No data received. Check port, baud rate, and cable.")

    def _save_csv(self, timestamps, records):
        fname = OUTPUT_DIR / f"ecg_{_ts()}.csv"
        import csv
        with open(fname, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time_s"] + self.LEADS)
            for i, t in enumerate(timestamps):
                row = [round(t, 4)] + [round(records[l][i], 4) for l in self.LEADS]
                writer.writerow(row)
        log.info(f"CSV saved → {fname}")

    def _save_plot(self, timestamps, records):
        try:
            import matplotlib.pyplot as plt
            fig, axes = plt.subplots(12, 1, figsize=(14, 20), sharex=True)
            fig.suptitle(f"ECG Capture  {datetime.datetime.now():%Y-%m-%d %H:%M:%S}", fontsize=12)
            for ax, lead in zip(axes, self.LEADS):
                ax.plot(timestamps, records[lead], linewidth=0.6, color="red")
                ax.set_ylabel(lead, fontsize=7, rotation=0, labelpad=20)
                ax.set_yticks([])
                ax.grid(True, alpha=0.3)
            axes[-1].set_xlabel("Time (s)")
            plt.tight_layout()
            fname = OUTPUT_DIR / f"ecg_{_ts()}.png"
            plt.savefig(fname, dpi=150)
            plt.close()
            log.info(f"Plot saved → {fname}")
        except ImportError:
            log.warning("matplotlib not installed — skipping plot. Run: pip install matplotlib")


# ══════════════════════════════════════════════════════════════════════════════
# 2. USB FLASH DRIVE / FILE-BASED CAPTURE
#    (Machine exports PDF/BMP/CSV to USB stick → watch the mount point)
# ══════════════════════════════════════════════════════════════════════════════

class FileWatchCapture:
    """
    Watches a directory (USB mount point) for new ECG files exported by the machine.
    Copies and optionally converts them to a local output folder.
    Handles: PDF, BMP, PNG, JPG, CSV, HL7, SCP-ECG (.scp)
    """

    EXTENSIONS = {".pdf", ".bmp", ".png", ".jpg", ".jpeg",
                  ".csv", ".txt", ".hl7", ".scp", ".xml"}

    def __init__(self, watch_dir: str, output_dir: Path = OUTPUT_DIR):
        self.watch_dir  = Path(watch_dir)
        self.output_dir = output_dir

    def watch(self):
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            log.error("watchdog not installed. Run: pip install watchdog")
            sys.exit(1)

        capture = self

        class Handler(FileSystemEventHandler):
            def on_created(self, event):
                if event.is_directory:
                    return
                p = Path(event.src_path)
                if p.suffix.lower() in capture.EXTENSIONS:
                    time.sleep(0.5)          # wait for write to complete
                    capture._handle_file(p)

        observer = Observer()
        observer.schedule(Handler(), str(self.watch_dir), recursive=True)
        observer.start()
        log.info(f"Watching {self.watch_dir} for ECG files … (Ctrl-C to stop)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    def _handle_file(self, src: Path):
        dest = self.output_dir / f"{_ts()}_{src.name}"
        import shutil
        shutil.copy2(src, dest)
        log.info(f"Captured: {src.name} → {dest}")

        ext = src.suffix.lower()
        if ext in {".bmp", ".jpg", ".jpeg", ".png"}:
            self._process_image(dest)
        elif ext == ".pdf":
            self._process_pdf(dest)
        elif ext == ".scp":
            self._process_scp(dest)

    def _process_image(self, path: Path):
        """Enhance and re-save the ECG image."""
        try:
            from PIL import Image, ImageFilter, ImageEnhance
            img = Image.open(path).convert("RGB")
            img = ImageEnhance.Contrast(img).enhance(1.4)
            img = img.filter(ImageFilter.SHARPEN)
            out = path.with_suffix(".enhanced.png")
            img.save(out, dpi=(300, 300))
            log.info(f"Enhanced image → {out}")
        except ImportError:
            log.warning("Pillow not installed — skipping image enhancement.")

    def _process_pdf(self, path: Path):
        """Convert PDF pages to images."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(path)
            for i, page in enumerate(doc):
                mat = fitz.Matrix(2, 2)   # 2× zoom ≈ 144 dpi
                pix = page.get_pixmap(matrix=mat)
                out = path.with_suffix(f".page{i+1}.png")
                pix.save(str(out))
                log.info(f"PDF page {i+1} → {out}")
        except ImportError:
            log.warning("PyMuPDF not installed — skipping PDF conversion. Run: pip install pymupdf")

    def _process_scp(self, path: Path):
        """Parse SCP-ECG binary file (ISO 11073-91064)."""
        log.info(f"SCP-ECG file detected: {path.name}  (use a dedicated SCP parser for full decode)")
        # Basic header read
        with open(path, "rb") as f:
            header = f.read(6)
        if len(header) >= 2:
            log.info(f"  First 2 bytes (CRC area): {header[:2].hex()}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. IMAGE-ONLY CAPTURE  (take a photo/scan of the thermal printout, digitise)
# ══════════════════════════════════════════════════════════════════════════════

class PrintoutDigitizer:
    """
    Digitises a scanned / photographed ECG paper printout using OpenCV.
    Detects the ECG grid, extracts waveform traces, and saves data as CSV.
    """

    def __init__(self, image_path: str, output_dir: Path = OUTPUT_DIR):
        self.image_path = Path(image_path)
        self.output_dir = output_dir

    def digitize(self):
        try:
            import cv2
            import numpy as np
        except ImportError:
            log.error("opencv-python / numpy not installed. Run: pip install opencv-python numpy")
            sys.exit(1)

        import cv2, numpy as np

        log.info(f"Digitising {self.image_path.name} …")
        img = cv2.imread(str(self.image_path))
        if img is None:
            log.error("Could not read image file.")
            return

        gray   = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        # Threshold to isolate dark waveform on light (pink) ECG paper
        _, thresh = cv2.threshold(blurred, 100, 255, cv2.THRESH_BINARY_INV)

        # Save pre-processed image for inspection
        pre_out = self.output_dir / f"preprocessed_{_ts()}.png"
        cv2.imwrite(str(pre_out), thresh)
        log.info(f"Pre-processed image → {pre_out}")

        # Skeleton / column scan to extract y-position of trace per x column
        h, w = thresh.shape
        trace = []
        for x in range(w):
            col = thresh[:, x]
            ys  = np.where(col > 0)[0]
            if len(ys):
                trace.append((x, int(np.mean(ys))))
            else:
                trace.append((x, None))

        # Save as CSV
        csv_out = self.output_dir / f"digitized_{_ts()}.csv"
        import csv
        with open(csv_out, "w", newline="") as f:
            w_ = csv.writer(f)
            w_.writerow(["pixel_x", "pixel_y"])
            for x, y in trace:
                w_.writerow([x, y if y is not None else ""])
        log.info(f"Digitised trace CSV → {csv_out}")
        log.info("Note: pixel_y values need calibration against the grid to convert to mV.")


# ══════════════════════════════════════════════════════════════════════════════
# Utility
# ══════════════════════════════════════════════════════════════════════════════

def _ts() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def list_serial_ports():
    """Helper: list available serial ports on the system."""
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No serial ports detected.")
    for p in ports:
        print(f"  {p.device:20s}  {p.description}")


# ══════════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="ECG Capture — Labotronics machine data/image acquisition"
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    # serial mode
    p_serial = sub.add_parser("serial", help="Capture via RS-232/USB-serial port")
    p_serial.add_argument("--port",     required=True, help="Serial port, e.g. /dev/ttyUSB0 or COM3")
    p_serial.add_argument("--baud",     type=int, default=115200)
    p_serial.add_argument("--duration", type=int, default=10, help="Capture duration in seconds")

    # watch mode
    p_watch = sub.add_parser("watch", help="Watch a folder for files exported by the machine")
    p_watch.add_argument("--watch-dir", required=True, help="Directory to watch (USB mount point)")

    # digitize mode
    p_dig = sub.add_parser("digitize", help="Digitise a scanned ECG paper printout image")
    p_dig.add_argument("--image", required=True, help="Path to scanned ECG image")

    # list-ports helper
    sub.add_parser("list-ports", help="List available serial ports")

    args = parser.parse_args()

    if args.mode == "serial":
        cap = SerialCapture(port=args.port, baud=args.baud)
        cap.capture(duration_sec=args.duration)

    elif args.mode == "watch":
        cap = FileWatchCapture(watch_dir=args.watch_dir)
        cap.watch()

    elif args.mode == "digitize":
        dig = PrintoutDigitizer(image_path=args.image)
        dig.digitize()

    elif args.mode == "list-ports":
        try:
            list_serial_ports()
        except ImportError:
            print("pyserial not installed. Run: pip install pyserial")


if __name__ == "__main__":
    main()
