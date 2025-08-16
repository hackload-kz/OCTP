__all__ = ("create_app",)

import functools
import logging
from contextlib import asynccontextmanager

import fastapi
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from redis import asyncio as aioredis
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from config import Environment
from config import Settings

from .caching import set_redis_cache

# from .database import SessionLocal
from .database import set_async_engine
from .exceptions import ApplicationError
from .handlers import application_error_handler
from .handlers import handler400
from .handlers import handler403
from .handlers import handler404
from .handlers import handler408
from .handlers import handler500
from .handlers import handler504
from .handlers import http_exception_handler
from .handlers import not_implemented_error_handler
from .handlers import request_validation_error_handler
from .middlewares import ContentLengthMiddleware
from .middlewares import DBSessionMiddleware
from .middlewares import RequestContextMiddleware
from .middlewares import SessionMiddleware
from .openapi import custom_openapi

logger = logging.getLogger(__name__)


def create_app(settings: Settings) -> fastapi.FastAPI:
    app_configs = {
        "title": settings.APP_NAME,
        "version": settings.VERSION,
        "debug": settings.DEBUG,
        "openapi_url": "/api/schema/openapi.json",
        "docs_url": "/api/schema/swagger-ui/",
        "redoc_url": "/api/schema/redoc/",
    }
    # hide doc in production environment
    if settings.ENV == Environment.PROD:
        app_configs["openapi_url"] = None
    # show response time in debug mode
    if settings.DEBUG:
        app_configs["swagger_ui_parameters"] = {"displayRequestDuration": True}

    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    @asynccontextmanager
    # https://fastapi.tiangolo.com/advanced/events/#lifespan-events
    async def lifespan(_: fastapi.FastAPI):
        from anyio import CapacityLimiter
        from anyio.lowlevel import RunVar

        set_redis_cache(redis, settings.APP_NAME)
        set_async_engine(settings)

        # change fastapi/starlette default thread pool size for sync/blocking IO requests.
        # ref: https://github.com/tiangolo/fastapi/issues/4221
        RunVar("_default_thread_limiter").set(
            CapacityLimiter(settings.THREAD_POOL_SIZE)
        )
        yield

        from .database import engine

        await redis.close()
        await engine.dispose()

    app = fastapi.FastAPI(**app_configs, lifespan=lifespan)

    @app.get("/", include_in_schema=False)
    async def root(request: Request):
        return {"Hello": "world!"}

    @app.get("/health-check/")
    async def health_check():
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("health-check")
        return JSONResponse({"message": "ok"})

    # setup routers
    # from .users.api import router as accounts_router

    # app.include_router(accounts_router, prefix="/v1")

    # security middleswares
    app.add_middleware(
        CORSMiddleware,  # type: ignore
        allow_credentials=True,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        expose_headers=settings.CORS_EXPOSE_HEADERS,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)  # type: ignore
    app.add_middleware(ContentLengthMiddleware, max_length=settings.CONTENT_MAX_LENGTH)  # type: ignore
    app.add_middleware(GZipMiddleware, minimum_size=1024)  # type: ignore
    app.add_middleware(DBSessionMiddleware)  # type: ignore
    app.add_middleware(RequestContextMiddleware)  # type: ignore
    app.add_middleware(
        SessionMiddleware,  # type: ignore
        redis=redis,
        max_age=settings.SESSION_MAX_AGE,
        path=settings.SESSION_PATH,
        domain=settings.SESSION_DOMAIN,
        same_site=settings.SESSION_SAME_SITE,
        https_only=settings.SESSION_HTTPS_ONLY,
    )
    if settings.ENV:
        app.add_middleware(HTTPSRedirectMiddleware)  # type: ignore

    # exception handlers
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(NotImplementedError, not_implemented_error_handler)

    # common http error handlers
    app.add_exception_handler(status.HTTP_400_BAD_REQUEST, handler400)
    app.add_exception_handler(status.HTTP_403_FORBIDDEN, handler403)
    app.add_exception_handler(status.HTTP_404_NOT_FOUND, handler404)
    app.add_exception_handler(status.HTTP_408_REQUEST_TIMEOUT, handler408)
    app.add_exception_handler(status.HTTP_500_INTERNAL_SERVER_ERROR, handler500)
    app.add_exception_handler(status.HTTP_504_GATEWAY_TIMEOUT, handler504)

    if settings.DEBUG:
        logger.setLevel(logging.DEBUG)

    # extending openapi
    app.openapi = functools.partial(custom_openapi, app)
    return app
