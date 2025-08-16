import json
from typing import Generic
from typing import TypeVar

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

T = TypeVar("T")


class HTTPExceptionModel(BaseModel):
    message: str


class ApplicationErrorModel(BaseModel):
    message: str
    code: str | int


class CustomModel(BaseModel):
    """Custom Pydantic model with additional methods"""

    def serializable_dict(self, **kwargs):
        """Return a dict which contains only serializable fields."""
        default_dict = self.model_dump(**kwargs)
        return jsonable_encoder(default_dict)

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, data):
        """Validate and convert a string to a dict."""
        if isinstance(data, str):
            return json.loads(data)
        return data


class Result(CustomModel, Generic[T]):
    """Generic response model"""

    total: int = Field(..., description="Total number of items")
    results: list[T] = Field(..., description="List of items")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 0,
                "results": [],
            }
        }
    )


class PaginatedResponse(CustomModel, Generic[T]):
    """Generic paginated response model"""

    count: int = Field(..., description="Total items count")
    next: str | None = Field(None, description="Link to the next page")
    previous: str | None = Field(None, description="Link to the previous page")
    results: list[T] = Field(..., description="List of items")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "count": 0,
                "next": None,
                "previous": None,
                "results": [],
            }
        }
    )


class User(CustomModel):
    """Stateless user model (backed by `validated` sso.mycar.kz  JWT tokens)"""

    user_id: int
    phone_number: str

    iin: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None

    role: int | None = Field(default=1)
    groups: list[str] | None = None
    scopes: list[str] | None = None
