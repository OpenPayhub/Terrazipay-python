from decimal import Decimal
from typing import Tuple
import json
from urllib.parse import quote as urlib_quote
from urllib.parse import parse_qs

from .alipay_config import (
    AlipayCredential,
    AlipayTradePayParams,
    AlipayTradeQueryParams,
)
from ...models import (
    AdapterDriver,
    GatewayConfig,
    OrderCreatorScheme,
    OrderSnapshot,
    OrderStatus,
)
from ...utils import (
    logger,
    error_context,
    AsyncRequest,
    sign_with_rsa2,
    verify_sign_rsa2,
    process_payload_to_json,
    is_currency_support
)
from ...utils.exceptions import *


SUPPORT_CURRENCY = {
    'CNY'
}

class AlipayDriver(AdapterDriver):
    def __init__(
        self,
        gateway: GatewayConfig,
        credentials: AlipayCredential,
        webhook_url: str| None = None,
        timeout: Decimal = 10.0,
        retry_codes: Tuple = (500, 502, 503, 504),
    ):
        self._gateway = gateway
        self._credentials = credentials
        self._webhook_url = webhook_url
        logger.debug(f"Init alipay gateway: {gateway}, credentials: {credentials}")
        self._requestor = AsyncRequest(timeout=timeout, retry_codes=retry_codes)

    async def create_order(self, order: OrderCreatorScheme) -> OrderSnapshot:
        if not self._credentials.APP_ID:
            logger.error("Alipay should input app_id, but got None")
            raise ServerCredentialError("Alipay should input app_id, but got None")

        logger.debug(f"Alipay order info: {order}")
        
        if not is_currency_support(order.currency, SUPPORT_CURRENCY):
            logger.error(f'{order.currency} is not supported in {SUPPORT_CURRENCY}')
            raise ServerConfigError(f'{order.currency} is not supported in {SUPPORT_CURRENCY}')

        params = AlipayTradePayParams(
            app_id=self._credentials.APP_ID,
            method=self._gateway.endpoints["page_pay"],
            format="JSON",
            charset="utf-8",
            sign_type="RSA2",
            timestamp=order.created_at,
            version="1.0",
            notify_url=self._webhook_url,
            return_url=order.server_gateway.return_url,
            biz_content=json.dumps(
                {
                    "out_trade_no": order.order_id,
                    "product_code": "FAST_INSTANT_TRADE_PAY",
                    "total_amount": str(order.amount),
                    "subject": order.description,
                },
                separators=(",", ":"),
            ),
        ).model_dump(exclude_none=True)

        sign = sign_with_rsa2(params, self._credentials.PRIVATE_KEY)
        params["sign"] = sign

        paylink = f"{self._gateway.base_url}?" + "&".join(
            f"{k}={urlib_quote(str(v))}" for k, v in params.items()
        )

        logger.debug(f"Sign with rsa2 and create paylink for {paylink}")
        logger.info("Create alipay order")

        return OrderSnapshot(
            order_id=order.order_id,
            status=OrderStatus.CREATED,
            payment_link=paylink,
            signature=sign,
            created_at=order.created_at,
        )


    async def capture_order(self, order_snapshot: OrderSnapshot) -> OrderSnapshot:
        logger.debug(f"Alipay no need for capture order: {order_snapshot}")
        return order_snapshot.replace(
            status=OrderStatus.CAPTURED
        )


    async def verify_webhook(
        self, header: dict, body: bytes, order_snapshot: OrderSnapshot
    ) -> OrderSnapshot:
        logger.debug(f"webhook for header: {order_snapshot}")
        decoded = body.decode("utf-8") if body else ""
        params = {k: v[0] for k, v in parse_qs(decoded).items()}
        logger.debug(f"Webhook with payload: {body}")
        try:
            if params.get("trade_status") == "TRADE_SUCCESS":
                sign = params.pop("sign", None)
                params.pop("sign_type", None)
                logger.debug(f"Sign for {sign}")
                if verify_sign_rsa2(params, sign, self._credentials.PUBLIC_KEY):
                    logger.warning("Verify signature failed params")
                    logger.debug(f"Verify params: {params}")
                    return order_snapshot.replace(
                        status=OrderStatus.WEBHOOKED,
                    )

        except Exception as e:
            error_info = error_context()
            logger.error(f"Error for {error_info}, Exception :{e}")
            raise ServerRequestError(error_info)

    @classmethod
    def extract_order_id(cls, header: dict, body: bytes) -> str:
        decoded = body.decode("utf-8") if body else ""
        params = {k: v[0] for k, v in parse_qs(decoded).items()}
        return params["out_trade_no"]


    async def fetch_order_status(self, order_snapshot: OrderSnapshot) -> OrderSnapshot:
        logger.debug(f"Get order_snapshot for {order_snapshot}")
        biz_content = {
            "out_trade_no": order_snapshot.order_id,
            "query_options": ["trade_settle_info"],
        }
        params = AlipayTradeQueryParams(
            app_id=self._credentials.APP_ID,
            method=self._gateway.endpoints["trade_query"],
            format="JSON",
            charset="utf-8",
            sign_type="RSA2",
            timestamp=order_snapshot.created_at,
            version="1.0",
            biz_content=json.dumps(
                biz_content,
                separators=(",", ":"),
            ),
        ).model_dump(exclude_none=True)
        sign = sign_with_rsa2(params, self._credentials.PRIVATE_KEY)
        params["sign"] = sign
        response = await self._requestor.post(
            url=f"{self._gateway.base_url}", data=params
        )
        if response.status_code != 200:
            raise RuntimeError(f"Alipay HTTP error: {response.status_code}")

        payload = process_payload_to_json(
            payload=response.content, headers=response.headers
        )

        logger.debug(f"Alipay raw response: {payload}")
        query_response = payload.get("alipay_trade_query_response")
        if not query_response:
            raise RuntimeError("Invalid Alipay response structure")

        if query_response.get("out_trade_no") != order_snapshot.order_id:
            raise RuntimeError("order id incorrect")

        if query_response.get("code") != "10000":
            logger.debug(f"Alipay query payment failed for {query_response}")

            return order_snapshot.replace(status=OrderStatus.FAILED)


        status_mapping = {
            "TRADE_SUCCESS": OrderStatus.PAID,
            "TRADE_FINISHED": OrderStatus.PAID,
            "TRADE_CLOSED": OrderStatus.CANCEL,
        }
        trade_status = query_response.get("trade_status")
        new_status = status_mapping.get(trade_status, OrderStatus.FAILED)
        logger.info(
            f"Order {order_snapshot.order_id} "
            f"status={new_status} "
            f"trade_status={trade_status}"
        )
        return order_snapshot.replace(
            status=new_status
        )
