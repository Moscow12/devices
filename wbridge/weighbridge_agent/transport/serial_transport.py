"""Serial port transport for RS232/RS485 communication."""
from typing import Optional
import time

import serial
import structlog

logger = structlog.get_logger(__name__)


class SerialTransport:
    """Serial port communication handler."""

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        bytesize: int = 8,
        parity: str = 'N',
        stopbits: int = 1,
        timeout: float = 2.0,
        **kwargs
    ):
        """
        Initialize serial transport.

        Args:
            port: Serial port path (e.g., COM1, /dev/ttyUSB0)
            baudrate: Baud rate
            bytesize: Number of data bits
            parity: Parity ('N', 'E', 'O', 'M', 'S')
            stopbits: Number of stop bits
            timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self._connection: Optional[serial.Serial] = None
        self.logger = logger.bind(transport="serial", port=port)

    def connect(self) -> bool:
        """
        Open serial port connection.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout
            )
            self.logger.info(
                "Serial connection established",
                baudrate=self.baudrate
            )
            return True
        except serial.SerialException as e:
            self.logger.error(
                "Failed to open serial port",
                error=str(e)
            )
            return False

    def disconnect(self) -> bool:
        """
        Close serial port connection.

        Returns:
            True if successful, False otherwise
        """
        if self._connection and self._connection.is_open:
            try:
                self._connection.close()
                self.logger.info("Serial connection closed")
                return True
            except Exception as e:
                self.logger.error(
                    "Error closing serial port",
                    error=str(e)
                )
                return False
        return True

    def is_connected(self) -> bool:
        """Check if serial port is open."""
        return self._connection is not None and self._connection.is_open

    def read(self, size: int = 1024) -> Optional[str]:
        """
        Read data from serial port.

        Args:
            size: Maximum bytes to read

        Returns:
            Decoded string data or None on error
        """
        if not self.is_connected():
            self.logger.warning("Attempted to read from closed connection")
            return None

        try:
            data = self._connection.read(size)
            if data:
                decoded = data.decode('ascii', errors='ignore').strip()
                self.logger.debug("Received data", data=decoded)
                return decoded
            return None
        except Exception as e:
            self.logger.error("Error reading from serial port", error=str(e))
            return None

    def readline(self) -> Optional[str]:
        """
        Read a line from serial port (until newline).

        Returns:
            Decoded line or None on error
        """
        if not self.is_connected():
            return None

        try:
            line = self._connection.readline()
            if line:
                decoded = line.decode('ascii', errors='ignore').strip()
                self.logger.debug("Received line", data=decoded)
                return decoded
            return None
        except Exception as e:
            self.logger.error("Error reading line", error=str(e))
            return None

    def write(self, data: str) -> bool:
        """
        Write data to serial port.

        Args:
            data: String data to write

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            self.logger.warning("Attempted to write to closed connection")
            return False

        try:
            encoded = data.encode('ascii')
            self._connection.write(encoded)
            self.logger.debug("Sent data", data=data)
            return True
        except Exception as e:
            self.logger.error("Error writing to serial port", error=str(e))
            return False

    def flush(self):
        """Flush input and output buffers."""
        if self.is_connected():
            self._connection.reset_input_buffer()
            self._connection.reset_output_buffer()

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
