from typing import Tuple, Optional, Dict, Any, Union
from decimal import Decimal

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    retry_if_result,
)

from .loggers import logger
from .exceptions import *
from .tracebackers import error_context

class AsyncRequest:
    def __init__(
        self,
        timeout: Decimal = 10.0,
        retry_codes: Tuple[int, ...] = (500, 502, 503, 504)
    ):
        """
            :param timeout: Default request timeout in seconds.
        """
        self.timeout = timeout
        self.retry_codes = retry_codes
        # Standard HTTP status codes that warrant a retry (usually transient server issues)
        
    @retry(
        # Stops after the specified number of attempts (default 3)
        stop=stop_after_attempt(3),
        # Exponential backoff: e.g., wait 2s, 4s, 8s... between retries
        wait=wait_exponential(multiplier=1, min=2, max=10),
        # Retry if a network-level exception occurs OR if the status code is in our retry list
        retry=(
            retry_if_exception(
                lambda e: isinstance(e, (httpx.TimeoutException, httpx.NetworkError))
            )
            | retry_if_result(
                lambda res: isinstance(res, httpx.Response)
                and res.status_code in {500, 502, 504}
            )
        ),
        # Re-raise the last exception/response after all retries are exhausted
        reraise=True,
    )
    async def _request(
        self, 
        method: str, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Internal core request logic with retry and error handling.

        :param method: HTTP method (GET, POST, etc.)
        :param url: Target URL
        :param kwargs: Additional arguments passed to httpx.request (headers, params, json, etc.)
        :return: httpx.Response object
        :raises: httpx.HTTPStatusError for 4xx/5xx errors not handled by retry
        """
        # Allow overriding the default timeout per request

        async with httpx.AsyncClient(timeout=timeout or self.timeout) as client:
            logger.debug(f"Sending {method} request to {url}")
            response = await client.request(
                            method=method,
                            url=url,
                            headers=headers,
                            params=params,
                            data=data,
                            json=json,
                            **kwargs
                        )

            # If the status code is NOT in the retry list (500, 502, 504),
            # we check if it's an error (like 400 or 403) and raise immediately.
            if response.status_code not in self.retry_codes:
                return response
            try:
                response.raise_for_status()
                return response

            except Exception as e:
                errors = error_context()
                logger.error(
                    f"AsyncRequest failed for {e}, please check args: method: {method} | url: {url}",
                    f"Error context: {errors}",
                )
                raise RequestError("AysncRequest error")

            finally:
                logger.debug(f"Return finally: {response}")
                return response

    async def get(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None, **kwargs):
            return await self._request("GET", url, params=params, headers=headers, **kwargs)

    async def post(self, url: str, json: Optional[Any] = None, data: Optional[Any] = None, headers: Optional[Dict] = None, **kwargs):
        return await self._request("POST", url, json=json, data=data, headers=headers, **kwargs)

    async def put(self, url: str, json: Optional[Any] = None, headers: Optional[Dict] = None, **kwargs):
        return await self._request("PUT", url, json=json, headers=headers, **kwargs)

    async def delete(self, url: str, headers: Optional[Dict] = None, **kwargs):
        return await self._request("DELETE", url, headers=headers, **kwargs)