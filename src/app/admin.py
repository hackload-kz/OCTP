from sqladmin.authentication import (
    AuthenticationBackend as SQLAdminAuthenticationBackend,
)
from starlette.requests import Request
from starlette.responses import Response

from app.internal import auth_internal_user
from app.security import decode_token


class AuthenticationBackend(SQLAdminAuthenticationBackend):
    """Authentication backend for SQLAdmin routes."""

    def __init__(
        self,
        auth_group: str,
        public_key: str,
    ) -> None:
        self.auth_group = auth_group
        self.public_key = public_key
        self.middlewares = []

    async def login(self, request: Request) -> bool:
        form = await request.form()
        try:
            token = await auth_internal_user(form["username"], form["password"])
        except:  # noqa
            return False
        request.session.update({"access_token": token})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.pop("access_token", None)
        return True

    async def authenticate(self, request: Request) -> Response | bool:
        token = request.session.get("access_token")
        if not token:
            return False
        try:
            payload = decode_token(token, self.public_key)
        except:  # noqa
            return False
        return self.auth_group in payload["groups"]
