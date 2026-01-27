class BaseError(Exception):
    error_code: str = "UNKNOWN_ERROR"

    def __init__(
        self,
        message: str,
        *,
        context: dict | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.cause = cause

    def __str__(self):
        base = f"[{self.error_code}] {self.message}"
        if self.context:
            base += f" | context={self.context}"
        return base


class RequestError(BaseError):
    error_code = "RequestError"


class ServerRequestError(BaseError):
    error_code = "ServerRequestError"


class ClientRequestError(BaseError):
    error_code = "Bad client request"


class ServerCredentialError(BaseError):
    error_code = "Server Credential information error"


class ServerConfigError(BaseError):
    error_code = "Server config error"
    
class OrderError(BaseError):
    error_code = "OrderError"