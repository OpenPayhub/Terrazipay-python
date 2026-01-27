from typing import Sequence, Literal, Callable, Optional, Dict
from dataclasses import dataclass
from decimal import Decimal

from ..adapters.alipay import AlipayDriver, AlipayCredential, AlipayGateway
from ..adapters.paypal import PayPalCredential, PayPalGateway, PayPalDriver

from ..models import Environment, AdapterDriver
from ..utils import logger

@dataclass(frozen=True)
class Alipay:
    driver: AlipayDriver = AlipayDriver
    credential: AlipayCredential = AlipayCredential
    gateway: AlipayGateway = AlipayGateway

@dataclass(frozen=True)
class PayPal:
    driver: PayPalDriver = PayPalDriver
    credential: PayPalCredential = PayPalCredential
    gateway: PayPalGateway = PayPalGateway


ADAPTERS = {
    'alipay': Alipay,
    'paypal': PayPal
}


class AdapterRegistry:
    def __init__(self):
        self._adapters: dict[str, AdapterDriver] = {}

    def register(self, name: str, adapter_driver: AdapterDriver):
        self._adapters[name] = adapter_driver

    def get(self, name: str) -> AdapterDriver:
        if name not in self._adapters:
            raise KeyError(f"Adapter {name} not registered")
        return self._adapters[name]


class AdapterManager:
    def __init__(self):
        self._adapter_registry = AdapterRegistry()

    @classmethod
    async def create(
        cls,
        env: Environment,
        adapters: Sequence[Literal['alipay', 'paypal']],
        webhook_url: str | None = None,
        timeout: Decimal = Decimal("10.0"),
    ) -> "AdapterManager":
        self = cls()

        for adapter in adapters:
            name = adapter.lower()

            if name not in ADAPTERS:
                raise KeyError(f"Just support {list(ADAPTERS.keys())}, but got {adapter}")

            bundle = ADAPTERS[name]

            driver = bundle.driver(
                credentials=bundle.credential(_env_file=f".env.{env.value}"),
                gateway=getattr(bundle.gateway, env.name),
                webhook_url=webhook_url,
                timeout=timeout,
            )

            await driver.init()
            self._adapter_registry.register(name, driver)

        logger.info("Init adapters")
        logger.debug(f"Register: {adapters}, env: {env}, webhook_url:{webhook_url}")
        return self
    
    def get(self, name: str) -> AdapterDriver:
        return self._adapter_registry.get(name=name)

          
class AdapterDetector:
    """
    Detect payment adapter from HTTP headers.
    Maintains a registry for each adapter, so adding/modifying
    a platform is easy and centralized.
    """

    # registry：adapter_name -> detector function
    _registry: Dict[str, Callable[[Dict[str, str]], bool]] = {}

    @classmethod
    def register(cls, adapter_name: str, detect_func: Callable[[Dict[str, str]], bool]):
        """
        Register a adapter detection function.
        detect_func receives normalized headers dict, returns bool.
        """
        cls._registry[adapter_name] = detect_func

    @classmethod
    def detect(cls, headers: dict) -> Optional[str]:
        """
        Detect adapter from headers.
        Returns adapter_name or None.
        """
        if not headers:
            return None

        # normalize keys to lowercase
        normalized = {k.lower(): v for k, v in headers.items()}

        for adapter_name, detect_func in cls._registry.items():
            if detect_func(normalized):
                return adapter_name

        return None

def create_adapter_detector() -> AdapterDetector:
    detector = AdapterDetector()
    detector.register("stripe", lambda h: "user-agent" in h and "stripe" in h["user-agent"].lower())
    detector.register("paypal", lambda h: "user-agent" in h and "paypal" in h["user-agent"].lower())
    detector.register("alipay", lambda h: "user-agent" in h and "mozilla" in h["user-agent"].lower())
    detector.register("coinbase", lambda h: "user-agent" in h and "weipay" in h["user-agent"].lower())
    return detector