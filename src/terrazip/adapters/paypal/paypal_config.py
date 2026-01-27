from typing import Dict, List

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, BaseModel

from ...models import GatewayConfig, BaseGateway


class PayPalCredential(BaseSettings):
    CLIENT_ID: str = Field(alias="PAYPAL_CLIENT_ID")
    CLIENT_SECRET: str = Field(alias="PAYPAL_SECRET")
    WEBHOOK_ID: str = Field(alias="PAYPAL_WEBHOOK_ID")

    model_config = SettingsConfigDict(env_file=".env.sandbox", extra="ignore")

class PayPalGateway(BaseGateway):
    SANDBOX: GatewayConfig = GatewayConfig(
        base_url="https://api-m.sandbox.paypal.com",
        endpoints={
            "auth": "v1/oauth2/token",
            "create_order": "v2/checkout/orders",
            "capture_order": "v2/checkout/orders/{id}/capture",
        },
    )
    PRODUCTION: GatewayConfig = GatewayConfig(
        base_url="https://api-m.paypal.com",
        endpoints={
            "auth": "v1/oauth2/token",
            "create_order": "v2/checkout/orders",
            "capture_order": "v2/checkout/orders/{id}/capture",
        },
    )
    
class RawPurchaseUnits(BaseModel):
    reference_id: str
    amount: Dict
    
class PayPalCreateOrderRequestBody(BaseModel):
    intent: str = 'CAPTURE'
    payment_source: Dict
    purchase_units: List[RawPurchaseUnits]
    
class PayPalCreateOrderResponseBody(BaseModel):
    links: List[dict]

class Resource(BaseModel):
    purchase_units: List[RawPurchaseUnits] = Field(default_factory=list)

class PayPalWebhookResponsePayload(BaseModel):
    resource: Resource
    