from contextvars import ContextVar

from starlette.requests import Request

request_context: ContextVar[Request] = ContextVar("request")
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")
