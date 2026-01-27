# Terrazip

    面向 AI Agent 与开发者的聚合收款与支付框架

## 1. 环境配置

* **安装 uv**：
本项目推荐使用 [uv](https://docs.astral.sh/uv/getting-started/) 进行极速依赖管理和环境隔离

* **环境配置和安装依赖**：

    **安装依赖**：
    ```
    uv sync 
    ```

    **环境变量配置**
    由于不同的支付平台，有不同的授权规则，因此要求的环境变量也不同，目前支持在本项目根目录，创建.env.sandbox(测试沙盒) 或者 .env.production(生产环境)。

    1. 收款平台
    不同的支付平台获取授权方式，详见：
    支付宝：[alipay](../src/terrazip/adapters/alipay/README.cn.md)
    PayPal: [paypal](../src/terrazip/adapters/alipay/README.cn.md)

    2. AI agent：
    目前功能仍然属于demo， 如要运行示例， 要先安装 ai extra 的依赖:
    ```
    uv sync --extra ai
    ```
    详见：[ai](../src/terrazip/ai/README.cn.md)

    3. X402 ：
    先安装 x402 extra 的依赖：
    ```
    uv sync --extra x402
    ```
    详见: [x402_mock](../src/terrazip/x402_mock/README.cn.md)


* **收款链接示例**：

使用详情：[reference](reference.cn.md)

收款示例：

```
from fastapi import FastAPI

from src.terrazip.cores import TerrazipFastapi

app = FastAPI()

terrazip_fastapi = TerrazipFastapi(
    app=app,
    env='SANDBOX', # 这里修改为支付环境， 仅仅支持 sandbox 和 production 
    adapters=['alipay', 'paypal'], # 收款方式
    base_url="http://...", # 这里修改为基础域名 例如： localhost:5000
    webhook_base_url="https://...", # 这里修改为可被本地外访问的域名，可与base_url相同，本地调试可用 ngrok 
)

terrazip_fastapi.run()

```
订单完成事件
如果需要在订单完成后，执行自定义逻辑，需要进行事件注册，示例如下：

```
from src.terrazip.cores import OrderFailedEvent, OrderPaidEvent, AsyncEventBus

async def after_paid(event: OrderPaidEvent): # 目前仅支持事件 {"支付成功":"OrderPaidEvent", "支付失败":"OrderFailedEvent"}
    print(f"event: {event}")

event_bus = AsyncEventBus() # 初始化
event_bus.subscribe(OrderPaidEvent, after_paid) # 注册事件
terrazip_fastapi = TerrazipFastapi(
    ...
    event_bus=event_bus,
)

```



付款请求示例：

```
import httpx
import webbrowser

base_url = "http://localhost:5000"

payloads = {
    "adapter": "paypal",
    "amount": "10.0",
    "currency": "USD",
}

response = httpx.post(f"{base_url}/pay", json=payloads)
webbrowser.open(response.json().get("payment_link"))

```