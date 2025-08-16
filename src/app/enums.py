import enum


class Codes(enum.IntEnum):
    """Mycar API error codes."""

    OK = 0
    BAD_REQUEST = 1
    DOESNT_EXIST = 2
    OTP_INCORRECT = 3
    ALREADY_VERIFIED = 4
    EXPIRED = 5
    RETRY_COUNT_EXCEEDED = 6
    AUTHENTICATION_ERROR = 7
    TOKEN_EXPIRED = 8
    INVALID_DATA = 9
    USER_EXISTS = 10
    ALREADY_EXISTS_CODE = 11
    IIN_REQUIRED = 100
    CERTIFICATE_INVALID_PASSWORD = 101
    VERIFICATION_REQUIRED = 103
    VERIFICATION_FAILED = 104
    VERIFICATION_EXPIRED = 105
    LIVENESS_FAILED = 106


class Messages(str, enum.Enum):
    NOT_FOUND = "%s not found"
    ALREADY_EXISTS = "%s already exists"
    AUTHENTICATION_REQUIRED = "Authentication required"
    TOKEN_EXPIRED = "Token is expired"
    TOKEN_INVALID = "Token is invalid"
    INVALID_CREDENTIALS = "Invalid authentication credentials"
    INSUFFICIENT_PERMISSIONS = "Insufficient permissions"
    INVALID_REQUEST_DATA = "Invalid request data"
    REQUEST_GOT_SERVER_ERROR = "Request got server error"
    SERVICE_UNAVAILABLE = "%s service is unavailable"
    FILE_EXISTS_ERROR = "File exists at: %s"
    FILE_NOT_FOUND_ERROR = "File not found at %s"
    CERTIFICATE_INVALID_PASSWORD = "Invalid password for current certificate"
    LIVENESS_FAILED = "Liveness failed"
    VERIFICATION_REQUIRED = "Verification is required"
    VERIFICATION_FAILED = "Verification failed"
    VERIFICATION_EXPIRED = "Verification expired"
    IIN_REQUIRED = "iin is required"
    MYBRIDGE_PERSONAL_DATA_FAILED = "Failed to retrieve personal data."
