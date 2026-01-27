from typing import Dict, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from decimal import Decimal

from pydantic import BaseModel, Field, HttpUrl

class Environment(str, Enum):
    """Enumeration of supported environments."""
    SANDBOX = "sandbox"
    PRODUCTION = "production"


class GatewayConfig(BaseModel):
    """
    Stores gateway URLs and their corresponding endpoints.
    """
    # The base URL (e.g., https://openapi.alipay.com/gateway.do)
    base_url: HttpUrl
    
    # A mapping of business names to specific endpoint paths
    # e.g., {"create_order": "/v3/pay/transactions/jsapi"}
    endpoints: Dict[str, str] = Field(default_factory=dict)

    def get_url(self, action: str) -> str:
        """Helper to safely construct the full URL for a specific action."""
        path = self.endpoints.get(action, "")
        return f"{str(self.base_url).rstrip('/')}/{path.lstrip('/')}"


class BaseGateway(ABC):
    '''Differ sandbox and prod env gateway'''
    @property
    @abstractmethod
    def SANDBOX(self) -> GatewayConfig:
        pass
    
    @property
    @abstractmethod
    def PRODUCTION(self) -> GatewayConfig:
        pass


class ServerGateway(BaseModel):
    ''' The differ gateway after client click '''
    return_url: Union[str, HttpUrl] = Field(default='')
    cancel_url: Union[str, HttpUrl] = Field(default='')
