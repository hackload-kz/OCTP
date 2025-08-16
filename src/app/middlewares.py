import secrets
import typing
import uuid

from redis import asyncio as aioredis
from starlette import status
from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import HTTPConnection
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from starlette.types import Message
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send

from app.database import get_session

from .caching import RedisCache
from .context import correlation_id
from .context import request_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to set the request context for the current request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_context.set(request)
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        correlation_id.set(request_id[:8])  # set a short correlation ID
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class DBSessionMiddleware(BaseHTTPMiddleware):
    """Middleware to manage DB session commits and rollbacks."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        async for session in get_session(request):
            request.state.db = session
            try:
                response = await call_next(request)
                await session.commit()
                return response
            except Exception:
                await session.rollback()
                raise


class ContentLengthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        max_length: int = 1024 * 1024,  # 1 MB
    ) -> None:
        super().__init__(app)
        self._max_length = max_length

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.method == "POST":
            if "content-length" not in request.headers:
                return Response(status_code=status.HTTP_411_LENGTH_REQUIRED)
            # won't prevent an attacker from sending a valid `Content-Length`
            # https://github.com/fastapi/fastapi/issues/362#issuecomment-584104025
            content_length = int(request.headers["content-length"])
            if content_length > self._max_length:
                return Response(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        return await call_next(request)


class SessionMiddleware:
    """Drop-in replacement for Starlette's SessionMiddleware with cached sessions."""

    def __init__(
        self,
        app: ASGIApp,
        redis: aioredis.Redis,
        session_cookie: str = "session",
        max_age: int | None = 14 * 24 * 60 * 60,  # 14 days, in seconds
        path: str = "/",
        same_site: typing.Literal["lax", "strict", "none"] = "lax",
        https_only: bool = False,
        domain: str | None = None,
    ) -> None:
        self.app = app
        self.cache = RedisCache(redis, prefix=session_cookie)
        self.session_cookie = session_cookie
        self.max_age = max_age
        self.path = path
        self.security_flags = "httponly; samesite=" + same_site
        if https_only:  # Secure flag can be used with HTTPS only
            self.security_flags += "; secure"
        if domain is not None:
            self.security_flags += f"; domain={domain}"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)
        initial_session_was_empty = True

        if self.session_cookie in connection.cookies:
            value = connection.cookies[self.session_cookie]
            data = await self.cache.get(value)
            if data:
                scope["session"] = data
                initial_session_was_empty = False
            else:
                scope["session"] = {}
        else:
            value = None
            scope["session"] = {}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                if scope["session"]:
                    # We have session data to persist.
                    token = value or secrets.token_urlsafe(32)
                    await self.cache.set(token, scope["session"], self.max_age)
                    headers = MutableHeaders(scope=message)
                    header_value = "{session_cookie}={data}; path={path}; {max_age}{security_flags}".format(
                        session_cookie=self.session_cookie,
                        data=token,
                        path=self.path,
                        max_age=f"Max-Age={self.max_age}; " if self.max_age else "",
                        security_flags=self.security_flags,
                    )
                    headers.append("Set-Cookie", header_value)
                elif not initial_session_was_empty:
                    # The session has been cleared.
                    await self.cache.delete(value)
                    headers = MutableHeaders(scope=message)
                    header_value = "{session_cookie}={data}; path={path}; {expires}{security_flags}".format(
                        session_cookie=self.session_cookie,
                        data="null",
                        path=self.path,
                        expires="expires=Thu, 01 Jan 1970 00:00:00 GMT; ",
                        security_flags=self.security_flags,
                    )
                    headers.append("Set-Cookie", header_value)
            await send(message)

        await self.app(scope, receive, send_wrapper)
