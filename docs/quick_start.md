# Terrazip

    Unified Payment Framework for AI Agents and Developers

## 1. Environment Setup

* **Install uv**:
This project recommends using [uv](https://docs.astral.sh/uv/getting-started/) for ultra-fast dependency management and environment isolation

* **Environment Configuration and Dependency Installation**:

    **Install Dependencies**:
    ```
    uv sync 
    ```

    **Environment Variables Configuration**
    Different payment platforms have different authorization rules, so required environment variables vary. Currently supports creating .env.sandbox (test sandbox) or .env.production (production environment) in the project root directory.

    1. Payment Platforms
    Authorization methods for different payment platforms:
    Alipay: [alipay](../src/terrazip/adapters/alipay/README.md)
    PayPal: [paypal](../src/terrazip/adapters/alipay/README.md)

    2. AI Agent:
    Current functionality is still a demo. To run examples, first install ai extra dependencies:
    ```
    uv sync --extra ai
    ```
    See: [ai](../src/terrazip/ai/README.md)

    3. X402:
    First install x402 extra dependencies:
    ```
    uv sync --extra x402
    ```
    See: [x402_mock](../src/terrazip/x402_mock/README.md)

* **Payment Link Example**:

Usage Details: [reference](reference.md)

Payment Example:

```python
from fastapi import FastAPI
from src.terrazip.cores import TerrazipFastapi

app = FastAPI()
terrazip_fastapi = TerrazipFastapi(
    app=app,
    env='SANDBOX',  # Change to payment environment (SANDBOX or PRODUCTION)
    adapters=['alipay', 'paypal'],  # Payment methods
    base_url="http://...",  # Change to base domain (e.g., localhost:5000)
    webhook_base_url="https://...",  # Change to externally accessible domain (can be same as base_url, use ngrok for local testing)
)
terrazip_fastapi.run()
```

Order Completion Events
To execute custom logic after order completion, register events as follows:

```python
from src.terrazip.cores import OrderFailedEvent, OrderPaidEvent, AsyncEventBus

async def after_paid(event: OrderPaidEvent):  # Currently supports {"Payment Success":"OrderPaidEvent", "Payment Failure":"OrderFailedEvent"}
    print(f"event: {event}")

event_bus = AsyncEventBus()  # Initialize
event_bus.subscribe(OrderPaidEvent, after_paid)  # Register event
terrazip_fastapi = TerrazipFastapi(
    ...
    event_bus=event_bus,
)
```

Payment Request Example:

```python
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