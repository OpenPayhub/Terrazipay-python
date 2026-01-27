from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, BaseModel

from ...models import GatewayConfig, BaseGateway


class AlipayCredential(BaseSettings):
    PRIVATE_KEY: str = Field(alias="ALIPAY_APPLY_PRIVATE_KEY")
    PUBLIC_KEY: str = Field(alias="ALIPAY_PUBLIC_KEY")
    APP_ID: str = Field(alias="ALIPAY_APP_ID")
    model_config = SettingsConfigDict(env_file=".env.sandbox", extra="ignore")


class AlipayGateway(BaseGateway):
    SANDBOX: GatewayConfig = GatewayConfig(
        base_url="https://openapi-sandbox.dl.alipaydev.com/gateway.do",
        endpoints={
            "page_pay": "alipay.trade.page.pay",
            "trade_query": "alipay.trade.query",
        },
    )
    PRODUCTION: GatewayConfig = GatewayConfig(
        base_url="https://openapi.alipay.com/gateway.do",
        endpoints={
            "page_pay": "alipay.trade.page.pay",
            "trade_query": "alipay.trade.query",
        },
    )


class AlipayTradePayParams(BaseModel):
    app_id: str
    method: str
    format: str
    charset: str
    sign_type: str
    timestamp: str
    version: str
    notify_url: str
    return_url: str
    biz_content: str


class AlipayTradeQueryParams(BaseModel):
    app_id: str
    method: str
    format: str
    charset: str
    sign_type: str
    timestamp: str
    version: str
    biz_content: str
