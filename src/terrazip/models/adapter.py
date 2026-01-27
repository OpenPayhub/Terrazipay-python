from abc import ABC, abstractmethod

from .order import OrderSnapshot, OrderCreatorScheme


class AdapterDriver(ABC):
    is_support_capture_order = False
    
    async def init(self) -> None: ...

    @abstractmethod
    async def create_order(self, order: OrderCreatorScheme) -> OrderSnapshot: ...

    @abstractmethod
    async def capture_order(self, order_snapshot: OrderSnapshot) -> OrderSnapshot: ...

    @abstractmethod
    async def verify_webhook(
        self, header: dict, body: bytes, order_snapshot: OrderSnapshot
    ) -> OrderSnapshot: ...

    @classmethod
    @abstractmethod
    def extract_order_id(cls, header: dict, body: bytes) -> str: ...

    @abstractmethod
    async def fetch_order_status(self, order_snapshot: OrderSnapshot) -> OrderSnapshot: ...

    # @abstractmethod TODO ADD refund method
    # async def refund_order(self, order_id: str) -> None:
    #     ...
