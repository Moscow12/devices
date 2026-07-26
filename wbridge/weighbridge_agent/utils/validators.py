"""Data validation utilities."""
import re
from typing import Optional


def validate_weight(
    weight: float,
    min_weight: float = 0.0,
    max_weight: float = 999999.0
) -> bool:
    """
    Validate weight value is within acceptable range.

    Args:
        weight: Weight value to validate
        min_weight: Minimum acceptable weight
        max_weight: Maximum acceptable weight

    Returns:
        True if valid, False otherwise
    """
    return min_weight <= weight <= max_weight


def extract_number(text: str, pattern: Optional[str] = None) -> Optional[float]:
    """
    Extract numeric value from text using regex pattern.

    Args:
        text: Input text
        pattern: Regex pattern (default: matches decimal numbers)

    Returns:
        Extracted number or None if not found
    """
    if pattern is None:
        pattern = r'[-+]?\d*\.?\d+'

    match = re.search(pattern, text)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def extract_unit(text: str, pattern: Optional[str] = None) -> Optional[str]:
    """
    Extract unit from text using regex pattern.

    Args:
        text: Input text
        pattern: Regex pattern for units

    Returns:
        Extracted unit or None if not found
    """
    if pattern is None:
        pattern = r'\b(kg|lb|ton|t|g)\b'

    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return None


def check_stability(text: str, indicator: Optional[str] = "ST") -> bool:
    """
    Check if weight reading is stable.

    Args:
        text: Input text from indicator
        indicator: Stability indicator string

    Returns:
        True if stable, False otherwise
    """
    if indicator is None:
        return True
    return indicator in text
