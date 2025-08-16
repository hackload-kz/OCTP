from http import HTTPStatus

from fastapi.encoders import jsonable_encoder
from fastapi.utils import is_body_allowed_for_status_code
from starlette import status
from starlette.responses import JSONResponse
from starlette.responses import Response


async def handler400(request, exc) -> JSONResponse:
    code = HTTPStatus(status.HTTP_400_BAD_REQUEST)
    content = {"message": code.phrase if code.phrase == exc.detail else exc.detail}
    return JSONResponse(content, status.HTTP_400_BAD_REQUEST)


async def handler403(request, exc) -> JSONResponse:
    code = HTTPStatus(status.HTTP_403_FORBIDDEN)
    content = {"message": code.phrase if code.phrase == exc.detail else exc.detail}
    return JSONResponse(content, status.HTTP_403_FORBIDDEN)


async def handler404(request, exc) -> JSONResponse:
    code = HTTPStatus(status.HTTP_404_NOT_FOUND)
    content = {"message": code.phrase if code.phrase == exc.detail else exc.detail}
    return JSONResponse(content, status.HTTP_404_NOT_FOUND)


async def handler408(request, exc) -> JSONResponse:
    code = HTTPStatus(status.HTTP_408_REQUEST_TIMEOUT)
    content = {"message": code.phrase if code.phrase == exc.detail else exc.detail}
    return JSONResponse(content, status.HTTP_408_REQUEST_TIMEOUT)


async def handler500(request, exc) -> JSONResponse:
    code = HTTPStatus(status.HTTP_500_INTERNAL_SERVER_ERROR)
    content = {"message": code.phrase}
    return JSONResponse(content, status.HTTP_500_INTERNAL_SERVER_ERROR)


async def handler504(request, exc) -> JSONResponse:
    code = HTTPStatus(status.HTTP_504_GATEWAY_TIMEOUT)
    content = {"message": code.phrase}
    return JSONResponse(content, status.HTTP_504_GATEWAY_TIMEOUT)


async def not_implemented_error_handler(request, exc) -> JSONResponse:
    content = {"message": "Not implemented"}
    return JSONResponse(content, status.HTTP_202_ACCEPTED)


async def http_exception_handler(request, exc) -> Response | JSONResponse:
    """
    {
        "message": "Error message"
    }
    """
    headers = getattr(exc, "headers", None)
    if not is_body_allowed_for_status_code(exc.status_code):
        return Response(status_code=exc.status_code, headers=headers)
    content = {"message": exc.detail}
    return JSONResponse(content, status_code=exc.status_code, headers=headers)


async def value_error_handler(request, exc) -> JSONResponse:
    """
    {
        "message": "Validation Error"
        "fields": {}
    }
    """

    content = {"message": "Validation Error"}
    if len(exc.args) == 2:  # key, value
        content["fields"] = {exc.args[0]: exc.args[1]}
    return JSONResponse(content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


async def request_validation_error_handler(request, exc) -> JSONResponse:
    """
    {
        "message": "Validation Error",
        "fields": {}
    }
    """
    fields = {}
    for error in exc.errors():
        loc, msg = error["loc"], error["msg"]
        loc = loc[1:] if loc[0] in ("body", "query", "path") else loc
        fields[".".join(map(str, loc))] = msg
    content = {"message": "ValidationError", "fields": jsonable_encoder(fields)}
    return JSONResponse(content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


async def application_error_handler(request, exc) -> JSONResponse:
    """
    {
        "message": "Error message",
        "code": "code"
    }
    """
    content = {"message": exc.detail, "code": exc.code}
    return JSONResponse(content, status_code=exc.status_code, headers=exc.headers)
