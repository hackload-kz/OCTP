from copy import deepcopy
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from starlette import status

from app.enums import Codes
from app.enums import Messages
from app.schemas import ApplicationErrorModel
from app.schemas import HTTPExceptionModel


# https://fastapi.tiangolo.com/advanced/extending-openapi/
def custom_openapi(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        summary=app.summary,
        description=app.description,
        terms_of_service=app.terms_of_service,
        contact=app.contact,
        license_info=app.license_info,
        routes=app.routes,
        webhooks=app.webhooks.routes,
        tags=app.openapi_tags,
        servers=app.servers,
        separate_input_output_schemas=app.separate_input_output_schemas,
    )
    # look for the error 422 and removes it
    # https://github.com/tiangolo/fastapi/issues/1376
    http_methods = ["post", "get", "put", "delete"]
    for method in openapi_schema["paths"]:
        for m in http_methods:
            try:
                del openapi_schema["paths"][method][m]["responses"]["422"]
            except KeyError:
                pass
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def get_http_response(status_code: int, message: Messages | None = None):
    """Get openapi HTTP response for status code."""
    code = HTTPStatus(status_code)
    return {
        status_code: {
            "model": HTTPExceptionModel,
            "content": {
                "application/json": {
                    "examples": {
                        message if message else code: {
                            "summary": message.name if message else code.name,
                            "value": {
                                "message": message.value if message else code.phrase
                            },
                        },
                    }
                },
            },
        }
    }


def merge_responses(*responses: dict):
    """Merge responses into a single dictionary."""
    merged = {}
    for d in responses:
        for status_code, error_data in d.items():
            if status_code not in merged:
                merged[status_code] = deepcopy(error_data)
            else:
                examples = merged[status_code]["content"]["application/json"][
                    "examples"
                ]
                examples.update(error_data["content"]["application/json"]["examples"])
    return merged


TOKEN_INVALID = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ApplicationErrorModel,
        "content": {
            "application/json": {
                "examples": {
                    Messages.TOKEN_INVALID: {
                        "summary": Messages.TOKEN_INVALID.name,
                        "value": {
                            "message": Messages.TOKEN_INVALID.value,
                            "code": Codes.AUTHENTICATION_ERROR,
                        },
                    },
                }
            },
        },
    }
}

TOKEN_EXPIRED = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ApplicationErrorModel,
        "content": {
            "application/json": {
                "examples": {
                    Messages.TOKEN_EXPIRED: {
                        "summary": Messages.TOKEN_EXPIRED.name,
                        "value": {
                            "message": Messages.TOKEN_EXPIRED.value,
                            "code": Codes.TOKEN_EXPIRED,
                        },
                    },
                }
            },
        },
    }
}

AUTHENTICATION_REQUIRED = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": HTTPExceptionModel,
        "content": {
            "application/json": {
                "examples": {
                    Messages.AUTHENTICATION_REQUIRED: {
                        "summary": Messages.AUTHENTICATION_REQUIRED.name,
                        "value": {"message": Messages.AUTHENTICATION_REQUIRED.value},
                    },
                }
            },
        },
    }
}

INVALID_CREDENTIALS = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": HTTPExceptionModel,
        "content": {
            "application/json": {
                "examples": {
                    Messages.INVALID_CREDENTIALS: {
                        "summary": Messages.INVALID_CREDENTIALS.name,
                        "value": {"message": Messages.INVALID_CREDENTIALS.value},
                    },
                }
            },
        },
    }
}

INSUFFICIENT_PERMISSIONS = {
    status.HTTP_403_FORBIDDEN: {
        "model": HTTPExceptionModel,
        "content": {
            "application/json": {
                "examples": {
                    Messages.INSUFFICIENT_PERMISSIONS: {
                        "summary": Messages.INSUFFICIENT_PERMISSIONS.name,
                        "value": {"message": Messages.INSUFFICIENT_PERMISSIONS.value},
                    },
                }
            },
        },
    }
}

JWT_AUTHENTICATION = merge_responses(TOKEN_INVALID, TOKEN_EXPIRED)
