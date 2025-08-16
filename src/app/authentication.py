import logging

from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBasicCredentials
from otel import instrument

from config import Settings
from config import get_settings

from ._auth.models import Token as AuthToken
from ._auth.services.token import TokenService
from .enums import Messages
from .exceptions import AuthenticationError
from .internal import auth_internal_user
from .schemas import User
from .security import basic_scheme
from .security import bearer_scheme
from .security import decode_token
from .security import token_scheme

logger = logging.getLogger(__name__)


@instrument
async def basic_authentication(
    auth: HTTPBasicCredentials = Depends(basic_scheme),
    settings: Settings = Depends(get_settings),
) -> User:
    """Mycar SSO basic authentication dependency."""
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Messages.AUTHENTICATION_REQUIRED,
            headers={"WWW-Authenticate": "Basic"},
        )
    token = await auth_internal_user(**auth.model_dump())
    payload = decode_token(token, settings.SSO_TOKEN_PUBLIC_KEY)
    user = User(**payload)
    if settings.SSO_AUTH_GROUP not in user.groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=Messages.INSUFFICIENT_PERMISSIONS,
        )
    return user


@instrument
async def jwt_authentication(
    auth: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> User:
    """Mycar SSO JWT authentication dependency."""
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Messages.AUTHENTICATION_REQUIRED,
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(auth.credentials, settings.SSO_TOKEN_PUBLIC_KEY)
    return User(**payload)


@instrument
async def token_authentication(
    auth: HTTPAuthorizationCredentials = Depends(token_scheme),
    service: TokenService = Depends(),
) -> AuthToken:
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Messages.AUTHENTICATION_REQUIRED,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await service.auth_token(auth.credentials)


@instrument
async def jwt_or_token_authentication(
    jwt_auth: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    token_auth: HTTPAuthorizationCredentials = Depends(token_scheme),
    service: TokenService = Depends(),
    settings: Settings = Depends(get_settings),
) -> AuthToken | User:
    if not jwt_auth and not token_auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Messages.AUTHENTICATION_REQUIRED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Try JWT parse
        payload = decode_token(jwt_auth.credentials, settings.SSO_TOKEN_PUBLIC_KEY)
        return User(**payload)
    except AuthenticationError:
        return await service.auth_token(token_auth.credentials)
