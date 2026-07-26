"""Avery Weigh-Tronix indicator parser."""
from datetime import datetime
from typing import Optional
import re

from ..base import BaseIndicator, WeightReading, ReadingStatus, WeightUnit
from ..registry import IndicatorRegistry
from ...transport.serial_transport import SerialTransport
from ...transport.tcp_transport import TCPTransport


@IndicatorRegistry.register("avery")
class AveryIndicator(BaseIndicator):
    """
    Avery Weigh-Tronix indicator.

    Supports ZM400 series and similar protocols.
    Format: <STX>ww.wwwuuC<ETX>
    Where: STX=0x02, ww.www=weight, uu=unit, C=checksum, ETX=0x03
    """

    def __init__(self, indicator_id: str, name: str, config: dict):
        """Initialize Avery indicator."""
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
            self.logger.info("Connected to Avery indicator")
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
            # Send weight request (W or P command)
            self.transport.write("W\r")

            # Read response
            raw_data = self.transport.readline()

            if raw_data:
                return self.parse_response(raw_data)
            return None

        except Exception as e:
            self.logger.error("Error reading weight", error=str(e))
            return None

    def parse_response(self, raw_data: str) -> Optional[WeightReading]:
        """
        Parse Avery protocol response.

        Common formats:
        - "   12345 kg"
        - "G    12.34 lb"  (G = Gross weight)
        - "N   123.45 kg"  (N = Net weight)
        """
        try:
            # Remove control characters
            cleaned = raw_data.strip()

            # Check for status indicators
            status_char = cleaned[0] if cleaned else ''
            is_stable = status_char in ['G', 'N', 'T']  # Gross, Net, Tare

            # Extract weight using regex
            weight_match = re.search(r'([-+]?\d+\.?\d*)\s*([a-zA-Z]+)', cleaned)

            if not weight_match:
                self.logger.warning("Could not parse Avery format", raw_data=raw_data)
                return None

            weight = float(weight_match.group(1))
            unit_str = weight_match.group(2)
            unit = self._normalize_unit(unit_str)

            # Determine status
            if 'OL' in cleaned.upper():
                status = ReadingStatus.OVERLOAD
            elif 'UL' in cleaned.upper():
                status = ReadingStatus.UNDERLOAD
            elif is_stable:
                status = ReadingStatus.STABLE
            else:
                status = ReadingStatus.UNSTABLE

            reading = WeightReading(
                weight=abs(weight),
                unit=unit,
                status=status,
                timestamp=datetime.now(),
                indicator_id=self.indicator_id,
                raw_data=raw_data,
                metadata={'type': status_char if status_char in ['G', 'N', 'T'] else 'G'}
            )

            return reading

        except Exception as e:
            self.logger.error(
                "Error parsing Avery response",
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
