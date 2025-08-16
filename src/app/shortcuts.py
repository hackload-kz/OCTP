from fastapi import HTTPException
from otel import instrument
from starlette import status

from app.enums import Messages
from app.repository import DatabaseRepository
from app.repository import Model
from app.repository import PK


@instrument
async def get_object_or_404(
    repository: DatabaseRepository[Model], *, pk: PK | None = None, **kwargs
) -> Model:
    """Get object by lookup parameters or raise 404 error."""
    if pk:
        instance = await repository.get(pk, **kwargs)
    else:
        instance = await repository.get_by(**kwargs)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=Messages.NOT_FOUND % repository.model.__name__,
        )
    return instance
