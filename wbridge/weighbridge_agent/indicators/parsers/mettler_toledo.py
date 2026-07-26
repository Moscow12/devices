"""Mettler Toledo indicator parser."""
from datetime import datetime
from typing import Optional
import re

from ..base import BaseIndicator, WeightReading, ReadingStatus, WeightUnit
from ..registry import IndicatorRegistry
from ...transport.serial_transport import SerialTransport
from ...transport.tcp_transport import TCPTransport


@IndicatorRegistry.register("mettler_toledo")
class MettlerToledoIndicator(BaseIndicator):
    """
    Mettler Toledo weighbridge indicator.

    Supports MT-SICS protocol (Standard Interface Command Set).
    Format: S S     12.345 kg\r\n
    Where: S = Stable, D = Dynamic, + = Positive, - = Negative
    """

    def __init__(self, indicator_id: str, name: str, config: dict):
        """Initialize Mettler Toledo indicator."""
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
            self.logger.info("Connected to Mettler Toledo indicator")
            # Send initialization command
            self.transport.write("@\r\n")  # Reset
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
            # Send weight request command
            self.transport.write("S\r\n")  # Send stable weight immediately

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
        Parse MT-SICS response.

        Format examples:
        - "S S     12.345 kg" (Stable, positive)
        - "D S    -12.345 kg" (Dynamic, negative)
        - "S I" (Stable, invalid/overload)
        """
        try:
            # MT-SICS format: [Status1] [Status2] [Sign][Weight] [Unit]
            # Example: "S S     12.345 kg"

            parts = raw_data.split()
            if len(parts) < 3:
                self.logger.warning("Invalid MT-SICS format", raw_data=raw_data)
                return None

            status1 = parts[0]  # S=Stable, D=Dynamic, etc.
            status2 = parts[1]  # S=Valid, I=Invalid, etc.

            # Determine status
            if status2 == 'I':
                status = ReadingStatus.OVERLOAD
                weight = 0.0
                unit = WeightUnit.KG
            else:
                # Extract weight and unit
                weight_str = parts[2] if len(parts) > 2 else "0"
                weight = float(weight_str)

                unit_str = parts[3] if len(parts) > 3 else "kg"
                unit = self._normalize_unit(unit_str)

                # Set status based on stability
                if status1 == 'S':
                    status = ReadingStatus.STABLE
                elif status1 == 'D':
                    status = ReadingStatus.UNSTABLE
                else:
                    status = ReadingStatus.ERROR

            reading = WeightReading(
                weight=abs(weight),  # Use absolute value
                unit=unit,
                status=status,
                timestamp=datetime.now(),
                indicator_id=self.indicator_id,
                raw_data=raw_data,
                metadata={'sign': '+' if weight >= 0 else '-'}
            )

            return reading

        except Exception as e:
            self.logger.error(
                "Error parsing MT-SICS response",
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
            't': WeightUnit.TON,
            'g': WeightUnit.GRAM
        }
        return mapping.get(unit_lower, WeightUnit.KG)
