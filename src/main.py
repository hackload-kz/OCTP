import logging.config
import sys

import uvicorn
from fastapi import FastAPI
from pydantic import ValidationError

from config import BASE_DIR
from config import get_settings

# pre-configure root logger
logging.basicConfig(format="%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    settings = get_settings()
except ValidationError as e:
    logger.error("ValidationError: %s", e)
    sys.exit(1)

from app import create_app  # noqa: E402

app: FastAPI = create_app(settings)

if __name__ == "__main__":
    log_config = str(BASE_DIR / "logging.yaml")
    uvicorn.run("main:app", reload=True, log_config=log_config, host="0.0.0.0")
