from starlette import status


class ApplicationError(Exception):
    """Application base error"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Application error"
    default_code = "application_error"

    def __init__(
        self,
        code: int | str = None,
        detail: str | None = None,
        headers: dict | None = None,
    ) -> None:
        self.code = code or self.default_code
        self.detail = detail or self.default_detail
        self.headers = headers


class AuthenticationError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication error"
    default_code = "authentication_error"


class AuthorizationError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Authorization error"
    default_code = "authorization_error"
