import base64
import secrets
import string
from enum import Enum
from functools import lru_cache
from typing import Any

import gostcrypto
import jwt
from fastapi.security import HTTPBasic
from fastapi.security import HTTPBearer
from nanoid.method import method
from otel import instrument
from passlib.context import CryptContext

from .enums import Codes
from .enums import Messages
from .exceptions import AuthenticationError

# sqladmin authentication
basic_scheme = HTTPBasic(
    scheme_name="Basic Authentication",
    description="MyCar Basic authentication",
    auto_error=False,
)
# jwt authentication
bearer_scheme = HTTPBearer(
    bearerFormat="JWT",
    scheme_name="JWT Authentication",
    description="Token should be formatted without `Bearer` prefix",
    auto_error=False,
)
# bearer authentication
token_scheme = HTTPBearer(
    scheme_name="Token Authentication",
    description="Token should be formatted without `Bearer` prefix",
    auto_error=False,
)


class JWTAlgorithm(Enum):
    HS256 = "HS256"  # deprecated
    RS256 = "RS256"

    @staticmethod
    def list():
        return list(map(lambda a: a.value, JWTAlgorithm))


@instrument
def decode_token(token: str, key: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, key, algorithms=JWTAlgorithm.list())
    except jwt.ExpiredSignatureError:
        raise AuthenticationError(
            code=Codes.TOKEN_EXPIRED,
            detail=Messages.TOKEN_EXPIRED,
        )
    except jwt.exceptions.PyJWTError:
        raise AuthenticationError(
            code=Codes.AUTHENTICATION_ERROR,
            detail=Messages.TOKEN_INVALID,
        )


@lru_cache
class PasswordHasher:
    def __init__(self, **options) -> None:
        # https://passlib.readthedocs.io/en/stable/lib/passlib.context.html
        if not options:
            options = {
                "schemes": ("bcrypt",),
                "deprecated": "auto",
            }
        self._context = CryptContext(**options)

    @instrument
    def verify(self, password: str, hashed_password: str) -> bool:
        return self._context.verify(password, hashed_password)

    @instrument
    def hash(self, password: str) -> str:
        return self._context.hash(password)


@instrument
def generate_key(prefix=None, alphabet=None, size=12) -> str:
    """Generate a random ID using nanoID algorithm."""

    if not alphabet:
        # default 62 characters [a-zA-Z0-9]
        alphabet = string.ascii_letters + string.digits

    # N-character key with possible M characters per position has M^N possible
    # combinations. The total entropy is N * log_2(M).
    key = method(
        algorithm=secrets.token_bytes,
        alphabet=alphabet,
        size=size,
    )
    return prefix + key if prefix else key


@instrument
def generate_gost_hash(data: bytes | bytearray) -> str:
    """GOST R 34.11-2012: Hash Function.
    Ref: https://www.rfc-editor.org/rfc/rfc6986.html
    """
    try:
        import _pystribog
    except ImportError:
        res = gostcrypto.gosthash.new("streebog512", data=data).digest()
    else:
        hasher = _pystribog.StribogHash(_pystribog.Hash512)
        hasher.update(data)
        res = hasher.digest()
    return base64.b64encode(res).decode("utf-8")  # type: ignore
