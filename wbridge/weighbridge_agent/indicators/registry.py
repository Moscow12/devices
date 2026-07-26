"""Indicator registry for auto-discovery and instantiation."""
from typing import Dict, Type, Optional
import structlog

from .base import BaseIndicator

logger = structlog.get_logger(__name__)


class IndicatorRegistry:
    """Registry for indicator types."""

    _indicators: Dict[str, Type[BaseIndicator]] = {}

    @classmethod
    def register(cls, indicator_type: str):
        """
        Decorator to register an indicator class.

        Usage:
            @IndicatorRegistry.register("generic_ascii")
            class GenericASCIIIndicator(BaseIndicator):
                pass
        """
        def decorator(indicator_class: Type[BaseIndicator]):
            cls._indicators[indicator_type] = indicator_class
            logger.info(
                "Registered indicator type",
                type=indicator_type,
                class_name=indicator_class.__name__
            )
            return indicator_class
        return decorator

    @classmethod
    def get(cls, indicator_type: str) -> Optional[Type[BaseIndicator]]:
        """Get indicator class by type."""
        return cls._indicators.get(indicator_type)

    @classmethod
    def list_types(cls) -> list:
        """List all registered indicator types."""
        return list(cls._indicators.keys())

    @classmethod
    def create_indicator(
        cls,
        indicator_type: str,
        indicator_id: str,
        name: str,
        config: dict
    ) -> Optional[BaseIndicator]:
        """
        Factory method to create indicator instance.

        Args:
            indicator_type: Type of indicator
            indicator_id: Unique ID
            name: Indicator name
            config: Configuration dict

        Returns:
            Indicator instance or None if type not found
        """
        indicator_class = cls.get(indicator_type)
        if indicator_class is None:
            logger.error(
                "Unknown indicator type",
                type=indicator_type,
                available_types=cls.list_types()
            )
            return None

        try:
            return indicator_class(
                indicator_id=indicator_id,
                name=name,
                config=config
            )
        except Exception as e:
            logger.exception(
                "Failed to create indicator",
                type=indicator_type,
                error=str(e)
            )
            return None
