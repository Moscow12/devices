"""Generic ASCII protocol parser for weighbridge indicators."""
from datetime import datetime
from typing import Optional
import re

from ..base import BaseIndicator, WeightReading, ReadingStatus, WeightUnit
from ..registry import IndicatorRegistry
from ...transport.serial_transport import SerialTransport
from ...transport.tcp_transport import TCPTransport
from ...utils.validators import extract_number, extract_unit, check_stability


@IndicatorRegistry.register("generic_ascii")
class GenericASCIIIndicator(BaseIndicator):
    """
    Generic ASCII protocol indicator.

    Supports most basic ASCII-based weighbridge indicators
    that output simple text format like: "Weight: 1234.5 kg ST"
    """

    def __init__(self, indicator_id: str, name: str, config: dict):
        """Initialize generic ASCII indicator."""
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

        # Parser configuration
        parser_config = config.get('parser', {})
        self.weight_pattern = parser_config.get('weight_pattern', r'\d+\.?\d*')
        self.unit_pattern = parser_config.get('unit_pattern', r'kg|lb|ton')
        self.stable_indicator = parser_config.get('stable_indicator')

    def connect(self) -> bool:
        """Connect to indicator."""
        self._is_connected = self.transport.connect()
        if self._is_connected:
            self.logger.info("Connected to generic ASCII indicator")
        return self._is_connected

    def disconnect(self) -> bool:
        """Disconnect from indicator."""
        success = self.transport.disconnect()
        self._is_connected = False
        if success:
            self.logger.info("Disconnected from indicator")
        return success

    def read_weight(self) -> Optional[WeightReading]:
        """Read weight from indicator."""
        if not self.is_connected():
            self.logger.warning("Not connected")
            return None

        try:
            # Read line from transport
            raw_data = self.transport.readline()

            if raw_data:
                return self.parse_response(raw_data)
            else:
                return None

        except Exception as e:
            self.logger.error("Error reading weight", error=str(e))
            return None

    def parse_response(self, raw_data: str) -> Optional[WeightReading]:
        """
        Parse raw ASCII response into WeightReading.

        Handles various ASCII formats:
        - "1234.5 kg"
        - "Weight: 1234.5 kg ST"
        - "1234.5kg STABLE"
        - etc.
        """
        try:
            # Extract weight value
            weight = extract_number(raw_data, self.weight_pattern)
            if weight is None:
                self.logger.warning("Could not extract weight", raw_data=raw_data)
                return None

            # Extract unit
            unit_str = extract_unit(raw_data, self.unit_pattern)
            if unit_str:
                unit = self._normalize_unit(unit_str)
            else:
                unit = WeightUnit.KG  # Default to kg

            # Check stability
            is_stable = check_stability(raw_data, self.stable_indicator)
            status = ReadingStatus.STABLE if is_stable else ReadingStatus.UNSTABLE

            # Check for overload/underload indicators
            if 'OL' in raw_data.upper() or 'OVER' in raw_data.upper():
                status = ReadingStatus.OVERLOAD
            elif 'UL' in raw_data.upper() or 'UNDER' in raw_data.upper():
                status = ReadingStatus.UNDERLOAD

            reading = WeightReading(
                weight=weight,
                unit=unit,
                status=status,
                timestamp=datetime.now(),
                indicator_id=self.indicator_id,
                raw_data=raw_data
            )

            self.logger.debug(
                "Parsed reading",
                weight=weight,
                unit=unit.value,
                status=status.value
            )

            return reading

        except Exception as e:
            self.logger.error(
                "Error parsing response",
                error=str(e),
                raw_data=raw_data
            )
            return None

    def _normalize_unit(self, unit_str: str) -> WeightUnit:
        """Normalize unit string to enum."""
        unit_lower = unit_str.lower()
        mapping = {
            'kg': WeightUnit.KG,
            'lb': WeightUnit.LB,
            'ton': WeightUnit.TON,
            't': WeightUnit.TON,
            'g': WeightUnit.GRAM
        }
        return mapping.get(unit_lower, WeightUnit.KG)
