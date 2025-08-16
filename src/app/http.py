import json
import logging
from http import HTTPStatus
from typing import Any

import aiohttp
from aiohttp.typedefs import StrOrURL
from fastapi import HTTPException
from starlette import status

logger = logging.getLogger(__name__)


class HttpClient:
    """Used to store and reuse single aiohttp.ClientSession"""

    def __init__(self, **kwargs):
        self.session = None
        self.kwargs = kwargs

    async def __call__(self) -> aiohttp.ClientSession:
        if not self.session:
            self.session = aiohttp.ClientSession(**self.kwargs)
        return self.session


class APIClient:
    """Base class for API clients"""

    name = None

    def __init__(self, session: aiohttp.ClientSession):
        self._session = session

    async def make_request(self, method: StrOrURL, url: str, **kwargs) -> Any:
        try:
            async with self._session.request(method, url, **kwargs) as response:
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    response_data = await response.json()
                else:
                    response_data = await response.read()
                response.raise_for_status()
                return response_data
        except aiohttp.ClientResponseError as e:
            try:
                if response_data and isinstance(response_data, dict | list):
                    log_data = json.dumps(response_data, indent=4, ensure_ascii=False)
                    logger.info(f"{self.name}, status {e.status}: \n{log_data}")
                else:
                    logger.info(f"{self.name}, status {e.status}: {response_data}")
            except (TypeError, json.JSONDecodeError):
                logger.info(
                    f"{self.name}, status {e.status}: Error parsing response data"
                )
            raise HTTPException(status_code=e.status, detail=e.message)
        except aiohttp.ClientError as e:
            message = f"{self.name}: {e}" if self.name else str(e)
            logger.error(message)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message
            )
        except TimeoutError:
            code = HTTPStatus(status.HTTP_504_GATEWAY_TIMEOUT)
            message = f"{self.name}: {code.phrase}" if self.name else code.phrase
            logger.error(message)
            raise HTTPException(status_code=code.value, detail=message)
