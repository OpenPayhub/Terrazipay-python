from typing import Literal, Dict, Optional, Callable, Awaitable, List, Type
from dataclasses import dataclass, field
import asyncio
from datetime import datetime
from abc import ABC
from collections import defaultdict

from .manager import AdapterManager
from ..models import AdapterDriver, OrderSnapshot, OrderStatus, OrderCreatorScheme
from ..utils import logger, error_context


"""
event_bus = AsyncEventBus()
async def after_paid(event: OrderPaidEvent):
    print(f"{event.order_id} is PAID")
    
event_bus.subscribe(OrderPaidEvent, after_paid)

"""


class DomainEvent(ABC):
    occurred_at: datetime


@dataclass(frozen=True)
class OrderPaidEvent(DomainEvent):
    order_id: str
    snapshot: OrderSnapshot
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class OrderFailedEvent(DomainEvent):
    order_id: str
    snapshot: OrderSnapshot
    occurred_at: datetime = field(default_factory=datetime.now)


EventHandler = Callable[[DomainEvent], Awaitable[None]]


class AsyncEventBus:
    def __init__(self):
        self._subscribers: Dict[Type[DomainEvent], List[EventHandler]] = defaultdict(
            list
        )

    def subscribe(
        self,
        event_type: Type[DomainEvent],
        handler: EventHandler,
    ):
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribe event_type:{event_type}, handler: {handler}")

    async def publish(self, event: DomainEvent):
        handlers = self._subscribers.get(type(event), [])

        for handler in handlers:
            asyncio.create_task(self._safe_handle(handler, event))

    async def _safe_handle(self, handler: EventHandler, event: DomainEvent):
        try:
            await handler(event)
        except Exception:
            error_info = error_context()
            logger.error(f"error_info: {error_info}")


class OrderContext:
    def __init__(
        self,
        driver: AdapterDriver,
        snapshot: OrderSnapshot,
        event_bus: Optional[AsyncEventBus] = None,
    ):
        self.driver = driver
        self.snapshot = snapshot
        self.event_bus = event_bus
        self.lock = asyncio.Lock()

    async def update_snapshot(self, new_snapshot: OrderSnapshot) -> bool:
        async with self.lock:
            old_status = self.snapshot.status

            if old_status in (OrderStatus.PAID, OrderStatus.FAILED, OrderStatus.CANCEL):
                return False

            self.snapshot = new_snapshot

        if self.event_bus:
            # EVENT PUBLISH OUT OF LOCK
            if (
                old_status != OrderStatus.PAID
                and new_snapshot.status == OrderStatus.PAID
            ):
                logger.info(f"Excution PAID event")
                await self.event_bus.publish(
                    OrderPaidEvent(
                        order_id=new_snapshot.order_id,
                        snapshot=new_snapshot,
                    )
                )

            if (
                old_status != OrderStatus.FAILED
                and new_snapshot.status == OrderStatus.FAILED
            ):
                logger.info(f"Excution FAILED event")
                await self.event_bus.publish(
                    OrderFailedEvent(
                        order_id=new_snapshot.order_id,
                        snapshot=new_snapshot,
                    )
                )

        return True


class OrderEngine:
    def __init__(
        self,
        adapter_manager: AdapterManager,
        event_bus: Optional[AsyncEventBus] = None,
        order_timeout_min: float = 15,
    ):
        self._adapter_manager = adapter_manager
        self.event_bus = event_bus
        self._orders: Dict[str, OrderContext] = {}
        self._watchers = {}
        self.order_timeout_min = order_timeout_min

    async def create_order(
        self, adapter: Literal["alipay", "paypal"], order: OrderCreatorScheme
    ) -> OrderSnapshot:
        if order.order_id in self._orders:
            raise ValueError(f"Order already exists: {order.order_id}")

        driver = self._adapter_manager.get(adapter)
        snapshot = await driver.create_order(order)

        self._orders[order.order_id] = OrderContext(
            driver=driver, snapshot=snapshot, event_bus=self.event_bus
        )
        watcher = OrderTimeoutWatcher(
            order_id=order.order_id,
            engine=self,
            timeout_seconds=self.order_timeout_min * 60,
        )
        watcher.start()

        self._watchers[order.order_id] = watcher

        logger.info(f"Order created: {order.order_id}, snapshot: {snapshot}")
        return snapshot

    async def apply_snapshot(self, snapshot: OrderSnapshot):
        context = self._orders.get(snapshot.order_id)
        if not context:
            raise KeyError(f"Unknown order: {snapshot.order_id}")

        is_update = await context.update_snapshot(new_snapshot=snapshot)
        if is_update:
            logger.info(f"Order {snapshot.order_id} " f"status -> {snapshot.status}")
            if snapshot.status in (
                OrderStatus.PAID,
                OrderStatus.FAILED,
                OrderStatus.CANCEL,
            ):
                watcher = self._watchers.pop(snapshot.order_id, None)
                if watcher:
                    await watcher.stop()

    def get_order_status(self, order_id: str) -> OrderStatus:
        return self._orders[order_id].snapshot.status

    def get_order_snapshot(self, order_id: str) -> OrderSnapshot:
        return self._orders[order_id].snapshot

    def list_orders(self) -> list[str]:
        return list(self._orders.keys())

    def get_order_driver(self, order_id: str) -> AdapterDriver:
        return self._orders[order_id].driver


class OrderTimeoutWatcher:
    def __init__(
        self,
        order_id: str,
        engine: OrderEngine,
        timeout_seconds: int,
        interval_seconds: int = 10,
    ):
        self.order_id = order_id
        self.engine = engine
        self.timeout_seconds = timeout_seconds
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    def start(self):
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        self._stop_event.set()
        if self._task:
            self._task.cancel()

    async def _run(self):
        try:
            await asyncio.wait_for(
                self._stop_event.wait(),
                timeout=self.timeout_seconds,
            )
            return

        except asyncio.TimeoutError:
            try:
                logger.info(f"Order {self.order_id} reached timeout, verifying...")
                driver = self.engine.get_order_driver(self.order_id)
                snapshot = self.engine.get_order_snapshot(self.order_id)
                new_snapshot = await driver.fetch_order_status(snapshot)
                await self.engine.apply_snapshot(new_snapshot)
                logger.debug(f"Timeout watcher trigger: {self.order_id}")
            except Exception as e:
                error_info = error_context()
                logger.error(
                    f"Failed to query order {self.order_id} on timeout: {e}, trace_error:{error_info}"
                )
        except Exception as e:
            error_info = error_context()
            logger.error(f"Watcher unexpected error: {e}, trace_error:{error_info}")
