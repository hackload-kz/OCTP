import logging

import aiohttp
from fastapi import HTTPException
from fastapi import status

from config import get_settings

from .caching import cached
from .enums import Codes
from .enums import Messages
from .exceptions import ApplicationError
from .exceptions import AuthenticationError
from .http import HttpClient

logger = logging.getLogger(__name__)

http_client = HttpClient(
    timeout=aiohttp.ClientTimeout(total=30),
    raise_for_status=True,
)


@cached(ttl=24 * 60 * 60, namespace="sso")
async def get_internal_user(phone_number: str) -> int:
    """Internal call to sso.mycar.kz to get sso user."""
    logger.info("Get sso.mycar.kz user. phone_number=%s", phone_number)
    session = await http_client()
    settings = get_settings()
    try:
        async with session.post(
            url=settings.SSO_BASE_URL + "auth/internal-user/",
            data={"phone_number": phone_number},
            auth=aiohttp.BasicAuth(settings.SSO_AUTH_USER, settings.SSO_AUTH_PASS),
        ) as response:
            return (await response.json())["user_id"]
    except aiohttp.ClientResponseError as e:
        logger.warning("ClientResponseError: %s", e)
        raise HTTPException(e.status, f"SSO: {e.message}")
    except TimeoutError:
        logger.warning("TimeoutError: Request timeout")
        raise HTTPException(status.HTTP_408_REQUEST_TIMEOUT)
    except aiohttp.ClientError as e:
        logger.warning("ClientError: %s", e)
        raise ApplicationError(detail=f"SSO: {e}")


@cached(ttl=24 * 60 * 60, namespace="sso")
async def auth_internal_user(username: str, password: str) -> str:
    """Internal call to sso.mycar.kz to authenticate user."""
    logger.info("Auth sso.mycar.kz user. username=%s", username)
    session = await http_client()
    settings = get_settings()
    try:
        async with session.post(
            url=settings.SSO_BASE_URL + "auth/internal/",
            data={"username": username, "password": password},
        ) as response:
            return (await response.json())["access_token"]
    except aiohttp.ClientResponseError as e:
        logger.warning("ClientResponseError: %s", e)
        raise AuthenticationError(
            code=Codes.AUTHENTICATION_ERROR,
            detail=Messages.INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Basic"},
        )
    except TimeoutError:
        logger.warning("TimeoutError: Request timeout")
        raise HTTPException(status.HTTP_408_REQUEST_TIMEOUT)
    except aiohttp.ClientError as e:
        logger.warning("ClientError: %s", e)
        raise AuthenticationError(
            code=Codes.AUTHENTICATION_ERROR,
            headers={"WWW-Authenticate": "Basic"},
        )
