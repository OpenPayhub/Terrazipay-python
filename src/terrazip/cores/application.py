from typing import Literal, Sequence, Callable, Awaitable
import asyncio
from dataclasses import dataclass, field, asdict
from decimal import Decimal
from wsgiref.handlers import format_date_time
import time
from datetime import datetime
from typing import TypedDict, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import uvicorn

from ..models import Environment, ServerGateway, OrderCreatorScheme, OrderStatus, OrderSnapshot, AdapterDriver
from .engine import OrderEngine, AsyncEventBus
from ..utils import logger, create_order_uuid, process_payload_to_json, error_context
from .manager import create_adapter_detector, AdapterManager

ENVIORMENT = {
    'SANDBOX' : Environment.SANDBOX,
    'PRODUCTION' : Environment.PRODUCTION
}

class EndpointsConfig(TypedDict):
    success: str
    cancel: str
    webhook: str
    
@dataclass
class RequestCreateType:
    adapter: str
    amount: str
    currency: str
    description: str = field(default='Test Order')
    metadata: dict = field(default_factory=dict)

class Terrazip:
    def __init__(
        self,
        env: Literal['SANDBOX', 'PRODUCTION'],
        adapters: Sequence[Literal['alipay', 'paypal']],
        base_url: str,
        webhook_base_url: str,
        endpoints: Optional[EndpointsConfig] = None,
        event_bus: Optional[AsyncEventBus] = None,
        order_timeout_min: float = 15,
        timeout: Decimal = 10.0,
    ):
        self._env = ENVIORMENT.get(env)
        self._adapters = adapters
        self._base_url = base_url
        self._webhook_base_url = webhook_base_url
        self._endpoints = endpoints if endpoints else {
            "success": "/success",
            "cancel": "/cancel",
            "webhook": "/notify"
        }
        self.event_bus = event_bus
        self.order_timeout_min = order_timeout_min
        self._timeout = timeout
        self._detector = create_adapter_detector()
        
    async def init(self):
        self.adapter_manager = await AdapterManager.create(
            env=self._env,
            adapters=self._adapters,
            webhook_url=f"{self._webhook_base_url}{self._endpoints.get('webhook')}",
            timeout=self._timeout
        )
        self._engine = OrderEngine(
            adapter_manager=self.adapter_manager,
            event_bus=self.event_bus,
            order_timeout_min=self.order_timeout_min
        )
        logger.info(f"Init order engine")

    async def create_order(
        self,
        adapter: str,
        order_id: str,
        amount: str,
        currency: str,
        description: str = 'Test Order',
        metadata: dict| None = None,
    ):
        ordre_creator_scheme = OrderCreatorScheme(
            order_id=order_id,
            amount=Decimal(amount),
            currency=currency,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            server_gateway=ServerGateway(
                return_url=f"{self._base_url}{self._endpoints.get('success')}?order_id={order_id}",
                cancel_url=f"{self._base_url}{self._endpoints.get('cancel')}?order_id={order_id}"
            ),
            description=description,
            metadata=metadata or {}
        )
        return await self._engine.create_order(adapter=adapter, order=ordre_creator_scheme)
    
    async def capture_order(self, order_id: str):
        snapshot = await self._with_order(
            order_id,
            lambda d, s: d.capture_order(s),
        )
        if snapshot:
            logger.debug(f"order:{order_id}: capture -> {snapshot}")
        
    async def verify_webhook(self, order_id: str, header: dict, body: bytes):
        snapshot = await self._with_order(
            order_id,
            lambda d, s: d.verify_webhook(
                header=header,
                body=body,
                order_snapshot=s,
            ),
            skip_if_finished=True,
        )
        if snapshot:
            logger.debug(f"order:{order_id}: webhook -> {snapshot}")
        
    async def confirm_order_status(self, order_id: str):
        snapshot = await self._with_order(
            order_id=order_id,
            action=lambda d, s: d.fetch_order_status(s),
        )
        if snapshot:
            logger.debug(f"order:{order_id}: confirm new snapshort: {snapshot}")

    async def _with_order(
        self,
        order_id: str,
        action: Callable[[AdapterDriver, OrderSnapshot], Awaitable[OrderSnapshot]],
        *,
        skip_if_finished: bool = True,
    ) -> Optional[OrderSnapshot]:
        driver = self._engine.get_order_driver(order_id)
        snapshot = self._engine.get_order_snapshot(order_id)

        if skip_if_finished and snapshot.status in {
            OrderStatus.CANCEL,
            OrderStatus.PAID,
            OrderStatus.FAILED,
        }:
            logger.debug(f"Order:{order_id} already finished")
            return None

        new_snapshot = await action(driver, snapshot)
        await self._engine.apply_snapshot(new_snapshot)
        return new_snapshot

    def extract_order_id_from_request(self, header: dict, body: bytes) -> str:
        adapter_name = self._detector.detect(header)
        driver = self.adapter_manager.get(adapter_name)
        return driver.extract_order_id(header=header, body=body)


class TerrazipFastapi:
    def __init__(
        self,
        app: FastAPI,
        env: Literal['SANDBOX', 'PRODUCTION'],
        adapters: Sequence[Literal['alipay', 'paypal']],
        base_url: str,
        webhook_base_url: str,
        endpoints: Optional[EndpointsConfig] = None,
        event_bus: Optional[AsyncEventBus] = None,
        order_timeout_min: float = 15,
        timeout: Decimal = 10.0,
    ):
        self.endpoints = endpoints or {
            "success": "/success",
            "cancel": "/cancel",
            "webhook": "/notify"
        }
        self.terrazip = Terrazip(
            env=env,
            adapters=adapters,
            base_url=base_url,
            webhook_base_url=webhook_base_url,
            endpoints=self.endpoints,
            event_bus=event_bus,
            order_timeout_min=order_timeout_min,
            timeout=timeout,
        )
        self.app = app
        
    async def init(self):
        await self.terrazip.init()
    
    async def pay(self, request: Request) -> JSONResponse:
        body = await request.body()
        header = request.headers
        payload = process_payload_to_json(
            payload=body, headers=header
        )
        logger.debug(f"input request: header{header}, body: {payload}")
        try:
            request_type = RequestCreateType(**payload)
        except:
            error_info = error_context()
            logger.error(f"Error info:{error_info}")
            return JSONResponse(
                content={'text': 'Bad Request', 'error': {error_info}},
                status_code=400,
            )
        order_id = create_order_uuid('order')
        order_snapshot = await self.terrazip.create_order(
            adapter=request_type.adapter,
            order_id=order_id,
            amount=request_type.amount,
            currency=request_type.currency,
            description=request_type.description,
            metadata=request_type.metadata or {},
        )
        return JSONResponse(
            content=asdict(order_snapshot),
            status_code=200
        )
        
    async def success(self, order_id):
        await self.terrazip.capture_order(order_id=order_id)
        return JSONResponse(
            content='CAPTURE ORDER!',
            status_code=200
        )
        
    async def notify(self, request: Request):
        headers = request.headers
        body = await request.body()
        order_id = self.terrazip.extract_order_id_from_request(header=headers, body=body)
        await self.terrazip.verify_webhook(order_id, headers, body)
        await self.terrazip.confirm_order_status(order_id=order_id)
        return JSONResponse(
            content='Order Complete',
            status_code=200
        )
        
    def add_route(self, app: FastAPI):
        app.add_api_route('/pay', endpoint=self.pay, methods=["POST"])
        app.add_api_route(self.endpoints.get('success'), endpoint=self.success, methods=['GET'])
        app.add_api_route(self.endpoints.get('webhook'), endpoint=self.notify, methods=['POST'])
        
    def run(self, host: str='localhost', port: int=5000, app: FastAPI| None = None, log_level: str = 'info'):
        
        if not app:
            app = self.app
        self.add_route(app)
        
        async def start():
            await self.init()
            config = uvicorn.Config(app, host=host, port=port, log_level=log_level)
            server = uvicorn.Server(config)
            await server.serve()
            
        asyncio.run(start())
        
    def get_app(self) -> FastAPI:
        return self.app
