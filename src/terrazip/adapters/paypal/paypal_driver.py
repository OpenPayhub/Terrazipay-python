from decimal import Decimal
from typing import Tuple, Set

from .paypal_config import PayPalCredential, RawPurchaseUnits, PayPalCreateOrderRequestBody, PayPalCreateOrderResponseBody, PayPalWebhookResponsePayload
from ...utils import logger, error_context, AsyncRequest, is_currency_support, process_payload_to_json
from ...utils.exceptions import *
from ...models import OrderCreatorScheme, OrderSnapshot, AdapterDriver, GatewayConfig, OrderStatus


SUPPORT_CURRENCY = {
    "USD", "AUD", "BRL", "CAD", "CNY", "CZK", "DKK", "EUR", "HKD", "HUF", "ILS", "JPY", "MYR", "MXN", "TWD", "SGD"
}

class PayPalDriver(AdapterDriver):
    is_support_capture_order = True
    def __init__(
        self,
        gateway: GatewayConfig,
        credentials: PayPalCredential,
        webhook_url: str| None = None,
        timeout: Decimal = 10.0,
        retry_codes: Tuple = (500, 502, 503, 504),
    ):
        self._gateway = gateway
        self._credentials = credentials
        self._http = AsyncRequest(
            timeout=timeout,
            retry_codes=retry_codes
        )
        self.webhook_url = webhook_url
        
    async def init(self):
        self._access_token = await self._get_access_token()
        if self.webhook_url:
            await _is_webhook_valid(
                base_url=self._gateway.base_url,
                webhook_url=self.webhook_url,
                access_token=self._access_token
            )
        
    async def _get_access_token(self) -> str:
        """
        Authenticate with PayPal and retrieve an OAuth2 token.
        Demonstrates the use of post method with Basic Auth.
        """
        url = f"{self._gateway.base_url}{self._gateway.endpoints.get('auth')}"

        response = await self._http.post(
                url,
                data={"grant_type": "client_credentials"},
                auth=(self._credentials.CLIENT_ID, self._credentials.CLIENT_SECRET),
            )
        
        try:
            response_data = response.json()
            logger.debug(f"Response data: {response_data}")
        except Exception as e:
            error_info = error_context()
            logger.error(f"Request error:{error_info}, exception: {e}")
            raise ServerCredentialError(f"Request error:{error_info}, exception: {e}")
        
        if response_data:
            self._access_token = response_data["access_token"]
            logger.info("Got PayPal access token successfully!")
            return self._access_token

        logger.error("Got PayPal access token failed!")
        raise ConnectionError(
            "Got None response from Paypal Access token request, please check your USER info or web"
        )
    
    async def create_order(self, order: OrderCreatorScheme) -> OrderSnapshot:
        if not self._access_token:
            logger.error("Run get_access_token attri firstly, check your codes")
            raise RuntimeError("Run get_access_token firstly, check your codes")
        
        if not is_currency_support(order.currency, SUPPORT_CURRENCY):
            raise OrderError(f"Unsupport currency: {order.currency}, only support: {SUPPORT_CURRENCY}")
        
        headers = {
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._access_token}",
        }
        
        payload = PayPalCreateOrderRequestBody(
            payment_source={
                "paypal": {
                    "experience_context": {
                        "return_url": order.server_gateway.return_url,
                        "cancel_url": order.server_gateway.cancel_url,
                        "user_action": "PAY_NOW",
                    }
                }
            },
            purchase_units=[RawPurchaseUnits(
                reference_id=order.order_id,
                amount={
                    'currency_code': order.currency,
                    'value': str(order.amount)
                }
            ).model_dump()]
        ).model_dump()
        
        
        url = f"{self._gateway.base_url}{self._gateway.endpoints.get('create_order')}"
        logger.debug(f"Create order for {url} payloads: {payload}")
        try:
            response = await self._http.post(url, headers=headers, json=payload)
            response_payload = process_payload_to_json(payload=response.content, headers=response.headers)
            logger.debug(f'Create order payload:{response_payload}')
            response_body = PayPalCreateOrderResponseBody(
                links=response_payload.get('links')
            )
            payment_link = next(
                link.get("href")
                for link in response_body.links if link["rel"] in ("approve", "payer-action")
            )
            if not payment_link:
                raise RuntimeError(f"PayPal approve link missing: {response}")
            logger.debug(f"Got paypal paymentlink for {payment_link}")
            return OrderSnapshot(
                order_id=order.order_id,
                status=OrderStatus.CREATED,
                payment_link=payment_link,
                created_at=order.created_at,
                raw_response=response_payload,
            )
        except:
            error_info = error_context()
            logger.error(f"Paypal create order error for {error_info}")
            raise OrderError(f"Paypal create order error for {error_info}")
    
    async def capture_order(self, order_snapshot) -> OrderSnapshot:
        """
        PalPay is differ from other platform auot capture.
        This attr will be triggered after client click the payment methods bottom for
             return_url or EVENT for CHECKOUT.ORDER.APPROVE
        """ 
        if not self._access_token:
            raise RuntimeError("Run get_access_token attri firstly")
        
        capture_order_required_id = order_snapshot.raw_response.get("id")
        
        endpoint = self._gateway.endpoints.get("capture_order").format(id=capture_order_required_id)
        url = f"{self._gateway.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        logger.debug(f"capture order for paypal id: {capture_order_required_id}")
        try:
            response = await self._http.post(url, headers=headers)
            payloads = process_payload_to_json(response.content, response.headers)
            logger.debug(f"capture order payloads:{payloads}")
            
            status_event_map = {
                'APPROVED': OrderStatus.CAPTURED,
                'COMPLETED': OrderStatus.PAID,
                'VOIDED': OrderStatus.FAILED,
            }
            
            status = payloads.get('status')
            if status in status_event_map:
                logger.debug(f"status: {status} -> event_status: {status_event_map.get(status)}")
                return order_snapshot.replace(
                    status=status_event_map.get(status)
                )
            
            else:
                status = payloads.get('status')
                logger.debug(f'get unknown status:{status} for capture')
                raise OrderError(f'get unknown status:{status} for capture')

        except Exception as e:
            error_info = error_context()
            logger.error(f"Capture order get error:{error_info}, exception: {e}")
            raise OrderError(f"Capture order get error:{error_info}, exception: {e}")
    
    async def verify_webhook(self, header: dict, body: bytes, order_snapshot: OrderSnapshot) -> OrderSnapshot:
        payload = process_payload_to_json(payload=body, headers=header)
        if payload.get("event_type") == "CHECKOUT.ORDER.COMPLETED":
            try:
                is_verify = await _verify_paypal_webhook(
                    post_tool=self._http,
                    webhook_id=self._credentials.WEBHOOK_ID,
                    access_token=self._access_token,
                    base_url=self._gateway.base_url,
                    headers=header,
                    payload=payload
                )
                if is_verify:
                    logger.info("A PayPal order webhook complete")
                    return order_snapshot.replace(
                        status=OrderStatus.PAID
                    )
                    
            except Exception as e:
                error_info = error_context()
                logger.error(f"Webhook error: {error_info}, Exception: {e}")
                raise OrderError(f"Webhook error: {error_info}, Exception: {e}")

    @classmethod
    def extract_order_id(cls, header: dict, body: bytes) -> str:
        payload = process_payload_to_json(body, header)
        webhook_payload_obj = PayPalWebhookResponsePayload.model_validate(payload)
        if payload.resource.purchase_units:
            ref_id = webhook_payload_obj.resource.purchase_units[0].reference_id
            return ref_id
        raise OrderError(f"Got uptyped payload:{payload}")
    
    
    async def fetch_order_status(self, order_snapshot: OrderSnapshot) -> OrderSnapshot:
        if not self._access_token:
            raise RuntimeError("Run get_access_token attri firstly")
        
        fetch_order_required_id = order_snapshot.raw_response.get("id")
        
        endpoint = self._gateway.endpoints.get("capture_order").format(id=fetch_order_required_id)
        url = f"{self._gateway.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        logger.debug(f"fetch order for paypal id: {fetch_order_required_id}")
        try:
            response = await self._http.post(url, headers=headers)
            payloads = process_payload_to_json(response.content, response.headers)
            logger.debug(f"capture order payloads:{payloads}")
            if payloads.get('status') == 'COMPLETED':
                logger.info(f'order:{order_snapshot.order_id} captured completed!')
                return order_snapshot.replace(
                    status=OrderStatus.PAID,
                )
                
        except Exception as e:
            error_info = error_context()
            logger.error(f"Fetch order status error:{error_info}, Exception:{e}")
            raise OrderError(f"Fetch order status error:{error_info}, Exception:{e}")

    
async def _is_webhook_valid(base_url: str, webhook_url: str, access_token: str) -> bool:
    logger.info("Check Webhook status")
    request = AsyncRequest(timeout=5)
    webhook_set = await _list_webhook(request, base_url, access_token)
    if webhook_url in webhook_set:
        logger.info(
        f"{webhook_url} already exist in your PayPal webhook endpoint!"
        )
        return True
    
    logger.error(f"{webhook_url} is an invalid PayPal endpoint")
    raise ServerConfigError(
        f"Your webhook_endpoint: {webhook_url} was not setted in stripe, please check it in https://developer.paypal.com/dashboard/applications/edit/"
    )


        
async def _list_webhook(
    http_tool: AsyncRequest, base_url: str, access_token: str
) -> Set[str]:
    url = f"{base_url}v1/notifications/webhooks"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    response = await http_tool.get(url, headers=headers)
    try:
        payload = process_payload_to_json(response.content, response.headers)
        logger.debug(f"Get payload:{payload}")
    except:
        error_info = error_context()
        logger.error(f"get error info: {error_info}")
        raise ConnectionError(f"get error info: {error_info}")

    return {webhook.get("url") for webhook in payload["webhooks"]}

def _handle_paypal_webhook_info(headers: dict, payload: dict, webhook_id: str) -> dict:
    return {
        "auth_algo": headers.get("paypal-auth-algo"),
        "cert_url": headers.get("paypal-cert-url"),
        "transmission_id": headers.get("paypal-transmission-id"),
        "transmission_sig": headers.get("paypal-transmission-sig"),
        "transmission_time": headers.get("paypal-transmission-time"),
        "webhook_id": webhook_id,
        "webhook_event": payload,
    }
    
async def _verify_paypal_webhook(
    post_tool: AsyncRequest,
    webhook_id: str,
    access_token: str,
    base_url: str,
    headers: dict,
    payload: dict,
) -> bool:
    verify_url = f"{base_url}v1/notifications/verify-webhook-signature"
    data = _handle_paypal_webhook_info(
        headers=headers, payload=payload, webhook_id=webhook_id
    )
    try:
        response = await post_tool.post(
            verify_url,
            json=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
        )
        resp = process_payload_to_json(response.content, response.headers)
        if resp and resp.get("verification_status") == "SUCCESS":
            return True
        else:
            logger.warning(f"verification_status is not SUCCESS, response : {resp}")
            raise ValueError(f"verification_status is not SUCCESS")

    except:
        error_info = error_context()
        logger.error(f"Response verification_status: , error info: {error_info}")

    return False