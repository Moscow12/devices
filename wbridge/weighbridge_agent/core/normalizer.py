"""Data normalization for weight readings."""
from typing import Dict, Any, Optional
from datetime import datetime

import structlog

from ..indicators.base import WeightReading, WeightUnit

logger = structlog.get_logger(__name__)


class DataNormalizer:
    """
    Normalizes weight readings from different indicators into a standard format.
    """

    # Unit conversion factors to kilograms
    UNIT_CONVERSION = {
        WeightUnit.KG: 1.0,
        WeightUnit.LB: 0.453592,
        WeightUnit.TON: 1000.0,
        WeightUnit.GRAM: 0.001,
    }

    @staticmethod
    def normalize_unit(unit: str) -> WeightUnit:
        """
        Normalize unit string to WeightUnit enum.

        Args:
            unit: Unit string (kg, lb, ton, g, etc.)

        Returns:
            WeightUnit enum value
        """
        unit_lower = unit.lower().strip()

        unit_mapping = {
            'kg': WeightUnit.KG,
            'kgs': WeightUnit.KG,
            'kilogram': WeightUnit.KG,
            'kilograms': WeightUnit.KG,
            'lb': WeightUnit.LB,
            'lbs': WeightUnit.LB,
            'pound': WeightUnit.LB,
            'pounds': WeightUnit.LB,
            'ton': WeightUnit.TON,
            'tons': WeightUnit.TON,
            't': WeightUnit.TON,
            'g': WeightUnit.GRAM,
            'gram': WeightUnit.GRAM,
            'grams': WeightUnit.GRAM,
        }

        return unit_mapping.get(unit_lower, WeightUnit.KG)

    @staticmethod
    def convert_to_kg(weight: float, unit: WeightUnit) -> float:
        """
        Convert weight to kilograms.

        Args:
            weight: Weight value
            unit: Current unit

        Returns:
            Weight in kilograms
        """
        factor = DataNormalizer.UNIT_CONVERSION.get(unit, 1.0)
        return weight * factor

    @staticmethod
    def normalize_reading(reading: WeightReading, target_unit: Optional[WeightUnit] = None) -> Dict[str, Any]:
        """
        Normalize weight reading to standard format.

        Args:
            reading: WeightReading object
            target_unit: Target unit (default: keep original)

        Returns:
            Normalized dictionary
        """
        # Convert to target unit if specified
        if target_unit and target_unit != reading.unit:
            weight_kg = DataNormalizer.convert_to_kg(reading.weight, reading.unit)
            target_factor = DataNormalizer.UNIT_CONVERSION.get(target_unit, 1.0)
            normalized_weight = weight_kg / target_factor
            normalized_unit = target_unit
        else:
            normalized_weight = reading.weight
            normalized_unit = reading.unit

        return {
            'indicator_id': reading.indicator_id,
            'weight': round(normalized_weight, 2),
            'unit': normalized_unit.value,
            'status': reading.status.value,
            'timestamp': reading.timestamp.isoformat(),
            'raw_data': reading.raw_data,
            'metadata': reading.metadata or {}
        }

    @staticmethod
    def prepare_for_api(reading: WeightReading) -> Dict[str, Any]:
        """
        Prepare reading for API transmission.

        Args:
            reading: WeightReading object

        Returns:
            API-ready dictionary
        """
        return DataNormalizer.normalize_reading(reading)

    @staticmethod
    def validate_and_normalize(reading: WeightReading) -> Optional[Dict[str, Any]]:
        """
        Validate and normalize reading.

        Args:
            reading: WeightReading object

        Returns:
            Normalized dictionary or None if invalid
        """
        if not reading.is_valid():
            logger.warning(
                "Invalid reading, skipping",
                indicator_id=reading.indicator_id,
                status=reading.status.value
            )
            return None

        return DataNormalizer.normalize_reading(reading)
