from typing import Dict, Any
from dataclasses import dataclass, field, replace
from enum import Enum
from decimal import Decimal

from .config import ServerGateway


class OrderStatus(str, Enum):
    NEW = 'NEW'
    PAID = 'PAID'
    FAILED = 'FAILED'
    CREATED = 'CREATED'
    CAPTURED = 'CAPTURED'
    REFUNDED = 'REFUNDED'
    WEBHOOKED = 'WEBHOOKED'
    CANCEL = 'CANCEL'


@dataclass
class OrderSnapshot:
    order_id: str = field(default="")
    status: OrderStatus = field(default=OrderStatus.NEW)
    payment_link: str = field(default="")
    signature: str = field(default="")
    created_at: str = field(default="")
    raw_response: Dict[str, Any] | None = None

    def replace(self, **kwargs):
            """
            Create a new object, and apply replace
            """
            try:
                return replace(self, **kwargs)
            except TypeError as e:
                raise AttributeError(f"OrderSnapshot has no attribute: {e}")


@dataclass
class OrderCreatorScheme:
    order_id: str
    amount: Decimal
    currency: str
    created_at: str
    server_gateway: ServerGateway
    description: str = field(default="Test order")
    metadata: dict = field(default_factory=dict)
