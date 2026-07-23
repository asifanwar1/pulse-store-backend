import re
from decimal import ROUND_HALF_UP, Decimal


def slugify(value: str, fallback: str = "item") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def calculate_percentage_change(current: Decimal | int, previous: Decimal | int) -> Decimal:
    current = Decimal(current)
    previous = Decimal(previous)
    if previous == 0:
        if current == 0:
            return Decimal("0.00")
        return Decimal("100.00")
    return ((current - previous) / previous * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
