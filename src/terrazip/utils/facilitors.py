from typing import Collection
import uuid

def is_currency_support(input_currency: str, support_currency: Collection[str]) -> bool:
    return input_currency.upper() in support_currency


def create_order_uuid(prefix: str) -> str:
    """
    Create a globally unique order id.

    Example:
        tz_9f3c2a1b7d4e4c2f9c8b1a2e3d4f5a6b
    """
    if not prefix:
        raise ValueError("prefix must not be empty")

    return f"{prefix}_{uuid.uuid4().hex}"