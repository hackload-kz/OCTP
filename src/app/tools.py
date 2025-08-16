import logging

from fastapi.encoders import jsonable_encoder
from orjson import orjson

from .context import correlation_id


def orjson_dumps(v, *, default):
    # orjson.dumps returns bytes, to match standard json.dumps we need to decode
    return orjson.dumps(v, default=default).decode()


class ORJSONSerializer:
    @classmethod
    def encode(cls, value) -> str:
        # rely on fastapi jsonable_encoder.
        # note: some objects might not be encoded correctly. See:
        # https://docs.python.org/3/library/json.html#json.JSONEncoder.default
        return orjson_dumps(value, default=jsonable_encoder)

    @classmethod
    def decode(cls, value: str) -> str:
        return orjson.loads(value)


class CustomFilter(logging.Filter):
    """Used by python logging to filter logs and add correlation_id."""

    def __init__(self, levels=None):
        super().__init__()
        self._levels = levels

    def filter(self, record):
        record.correlation_id = correlation_id.get()
        return record.levelname in self._levels
