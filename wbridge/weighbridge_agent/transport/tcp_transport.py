"""TCP/IP transport for network-connected indicators."""
import socket
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class TCPTransport:
    """TCP/IP communication handler."""

    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 5.0,
        buffer_size: int = 1024,
        **kwargs
    ):
        """
        Initialize TCP transport.

        Args:
            host: IP address or hostname
            port: TCP port number
            timeout: Connection timeout in seconds
            buffer_size: Read buffer size
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.buffer_size = buffer_size
        self._socket: Optional[socket.socket] = None
        self.logger = logger.bind(
            transport="tcp",
            host=host,
            port=port
        )

    def connect(self) -> bool:
        """
        Establish TCP connection.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
            self.logger.info("TCP connection established")
            return True
        except socket.error as e:
            self.logger.error(
                "Failed to connect",
                error=str(e)
            )
            return False

    def disconnect(self) -> bool:
        """
        Close TCP connection.

        Returns:
            True if successful, False otherwise
        """
        if self._socket:
            try:
                self._socket.close()
                self.logger.info("TCP connection closed")
                return True
            except Exception as e:
                self.logger.error(
                    "Error closing socket",
                    error=str(e)
                )
                return False
        return True

    def is_connected(self) -> bool:
        """Check if TCP socket is connected."""
        if self._socket is None:
            return False

        try:
            # Try to peek at the socket without consuming data
            self._socket.setblocking(False)
            try:
                data = self._socket.recv(1, socket.MSG_PEEK)
                if len(data) == 0:
                    return False
            except BlockingIOError:
                # No data available, but socket is alive
                pass
            finally:
                self._socket.setblocking(True)
            return True
        except socket.error:
            return False

    def read(self, size: Optional[int] = None) -> Optional[str]:
        """
        Read data from TCP socket.

        Args:
            size: Bytes to read (uses buffer_size if None)

        Returns:
            Decoded string data or None on error
        """
        if not self.is_connected():
            self.logger.warning("Attempted to read from closed connection")
            return None

        try:
            size = size or self.buffer_size
            data = self._socket.recv(size)
            if data:
                decoded = data.decode('ascii', errors='ignore').strip()
                self.logger.debug("Received data", data=decoded)
                return decoded
            return None
        except socket.timeout:
            self.logger.debug("Read timeout")
            return None
        except Exception as e:
            self.logger.error("Error reading from socket", error=str(e))
            return None

    def readline(self, delimiter: bytes = b'\n') -> Optional[str]:
        """
        Read a line from TCP socket (until delimiter).

        Args:
            delimiter: Line delimiter

        Returns:
            Decoded line or None on error
        """
        if not self.is_connected():
            return None

        try:
            buffer = b''
            while True:
                chunk = self._socket.recv(1)
                if not chunk:
                    break
                buffer += chunk
                if delimiter in buffer:
                    break

            if buffer:
                decoded = buffer.decode('ascii', errors='ignore').strip()
                self.logger.debug("Received line", data=decoded)
                return decoded
            return None
        except socket.timeout:
            if buffer:
                decoded = buffer.decode('ascii', errors='ignore').strip()
                return decoded
            return None
        except Exception as e:
            self.logger.error("Error reading line", error=str(e))
            return None

    def write(self, data: str) -> bool:
        """
        Write data to TCP socket.

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
            self._socket.sendall(encoded)
            self.logger.debug("Sent data", data=data)
            return True
        except Exception as e:
            self.logger.error("Error writing to socket", error=str(e))
            return False

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
