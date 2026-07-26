"""Base indicator interface for all weighbridge indicators."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

import structlog

logger = structlog.get_logger(__name__)


class WeightUnit(Enum):
    """Standard weight units."""
    KG = "kg"
    LB = "lb"
    TON = "ton"
    GRAM = "g"


class ReadingStatus(Enum):
    """Weight reading status."""
    STABLE = "stable"
    UNSTABLE = "unstable"
    OVERLOAD = "overload"
    UNDERLOAD = "underload"
    ERROR = "error"
    NO_DATA = "no_data"


@dataclass
class WeightReading:
    """Normalized weight reading data structure."""
    weight: float
    unit: WeightUnit
    status: ReadingStatus
    timestamp: datetime
    indicator_id: str
    raw_data: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API transmission."""
        return {
            "weight": self.weight,
            "unit": self.unit.value,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "indicator_id": self.indicator_id,
            "raw_data": self.raw_data,
            "metadata": self.metadata or {}
        }

    def is_valid(self) -> bool:
        """Check if reading is valid for transmission."""
        return self.status in [ReadingStatus.STABLE, ReadingStatus.UNSTABLE]


class BaseIndicator(ABC):
    """
    Abstract base class for all weighbridge indicators.

    All indicator implementations must inherit from this class
    and implement the required methods.
    """

    def __init__(
        self,
        indicator_id: str,
        name: str,
        config: Dict[str, Any]
    ):
        """
        Initialize indicator.

        Args:
            indicator_id: Unique identifier for this indicator
            name: Human-readable name
            config: Configuration dictionary
        """
        self.indicator_id = indicator_id
        self.name = name
        self.config = config
        self.logger = logger.bind(
            indicator_id=indicator_id,
            indicator_name=name
        )
        self._is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the indicator.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        Close connection to the indicator.

        Returns:
            True if disconnection successful, False otherwise
        """
        pass

    @abstractmethod
    def read_weight(self) -> Optional[WeightReading]:
        """
        Read current weight from the indicator.

        Returns:
            WeightReading object if successful, None otherwise
        """
        pass

    @abstractmethod
    def parse_response(self, raw_data: str) -> Optional[WeightReading]:
        """
        Parse raw response from indicator into WeightReading.

        Args:
            raw_data: Raw string data from indicator

        Returns:
            Parsed WeightReading or None if parsing failed
        """
        pass

    def is_connected(self) -> bool:
        """Check if indicator is currently connected."""
        return self._is_connected

    def validate_reading(self, reading: WeightReading) -> bool:
        """
        Validate weight reading against configured rules.

        Args:
            reading: WeightReading to validate

        Returns:
            True if valid, False otherwise
        """
        validation_config = self.config.get('validation', {})
        min_weight = validation_config.get('min_weight', 0.0)
        max_weight = validation_config.get('max_weight', 999999.0)
        stable_required = validation_config.get('stable_required', False)

        # Check weight range
        if not (min_weight <= reading.weight <= max_weight):
            self.logger.warning(
                "Weight out of range",
                weight=reading.weight,
                min=min_weight,
                max=max_weight
            )
            return False

        # Check stability if required
        if stable_required and reading.status != ReadingStatus.STABLE:
            self.logger.debug(
                "Weight not stable",
                status=reading.status.value
            )
            return False

        return True

    def get_info(self) -> Dict[str, Any]:
        """
        Get indicator information.

        Returns:
            Dictionary with indicator details
        """
        return {
            "id": self.indicator_id,
            "name": self.name,
            "type": self.__class__.__name__,
            "connected": self._is_connected,
            "config": self.config
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"<{self.__class__.__name__}(id={self.indicator_id}, name={self.name})>"
