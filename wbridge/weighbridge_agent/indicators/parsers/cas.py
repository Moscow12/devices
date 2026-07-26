"""CAS CI-200 series indicator parser."""
from datetime import datetime
from typing import Optional
import re

from ..base import BaseIndicator, WeightReading, ReadingStatus, WeightUnit
from ..registry import IndicatorRegistry
from ...transport.serial_transport import SerialTransport
from ...transport.tcp_transport import TCPTransport


@IndicatorRegistry.register("cas")
class CASIndicator(BaseIndicator):
    """
    CAS CI-200 series indicator.

    Standard output format: ww.wwwuu S\r\n
    Where: ww.www=weight, uu=unit, S=status flag
    """

    def __init__(self, indicator_id: str, name: str, config: dict):
        """Initialize CAS indicator."""
        super().__init__(indicator_id, name, config)

        # Initialize transport
        transport_config = config['transport']
        transport_type = transport_config['type']

        if transport_type == 'serial':
            self.transport = SerialTransport(**transport_config)
        elif transport_type == 'tcp':
            self.transport = TCPTransport(**transport_config)
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")

    def connect(self) -> bool:
        """Connect to indicator."""
        self._is_connected = self.transport.connect()
        if self._is_connected:
            self.logger.info("Connected to CAS indicator")
        return self._is_connected

    def disconnect(self) -> bool:
        """Disconnect from indicator."""
        success = self.transport.disconnect()
        self._is_connected = False
        return success

    def read_weight(self) -> Optional[WeightReading]:
        """Read weight from indicator."""
        if not self.is_connected():
            return None

        try:
            # CAS indicators typically send data continuously
            # or respond to a simple request
            raw_data = self.transport.readline()

            if raw_data:
                return self.parse_response(raw_data)
            return None

        except Exception as e:
            self.logger.error("Error reading weight", error=str(e))
            return None

    def parse_response(self, raw_data: str) -> Optional[WeightReading]:
        """
        Parse CAS protocol response.

        Format examples:
        - "  1234.5 kg S" (Stable)
        - "  1234.5 kg U" (Unstable)
        - "    12.34 lb S"
        """
        try:
            # Clean up the data
            cleaned = raw_data.strip()

            # Extract weight, unit, and status
            # Pattern: optional spaces, number (possibly with decimal), spaces, unit, spaces, status
            match = re.match(
                r'\s*([-+]?\d+\.?\d*)\s*([a-zA-Z]+)\s*([SU])?',
                cleaned
            )

            if not match:
                self.logger.warning("Could not parse CAS format", raw_data=raw_data)
                return None

            weight = float(match.group(1))
            unit_str = match.group(2)
            status_flag = match.group(3) if match.group(3) else 'U'

            unit = self._normalize_unit(unit_str)

            # Determine status
            if status_flag == 'S':
                status = ReadingStatus.STABLE
            elif status_flag == 'U':
                status = ReadingStatus.UNSTABLE
            elif 'OL' in cleaned.upper():
                status = ReadingStatus.OVERLOAD
            else:
                status = ReadingStatus.UNSTABLE

            reading = WeightReading(
                weight=abs(weight),
                unit=unit,
                status=status,
                timestamp=datetime.now(),
                indicator_id=self.indicator_id,
                raw_data=raw_data
            )

            return reading

        except Exception as e:
            self.logger.error(
                "Error parsing CAS response",
                error=str(e),
                raw_data=raw_data
            )
            return None

    def _normalize_unit(self, unit_str: str) -> WeightUnit:
        """Normalize unit string to enum."""
        unit_lower = unit_str.lower().strip()
        mapping = {
            'kg': WeightUnit.KG,
            'lb': WeightUnit.LB,
            'ton': WeightUnit.TON,
            't': WeightUnit.TON,
            'g': WeightUnit.GRAM
        }
        return mapping.get(unit_lower, WeightUnit.KG)
