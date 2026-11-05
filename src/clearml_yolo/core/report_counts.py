"""Training-count validity without dataframe or workbook dependencies."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class TrainingCountIssue:
    """One class whose eligibility cannot be established from its training count."""

    model: str
    class_name: str
    field: str
    reason: str


def training_count(value: object) -> int | None:
    """Return an exact nonnegative integer, or None for unavailable/invalid data."""
    if value is None or isinstance(value, bool):
        return None
    try:
        count = Decimal(str(value))
    except InvalidOperation:
        return None
    if not count.is_finite() or count < 0 or count != count.to_integral_value():
        return None
    return int(count)
