__all__ = (
    "BaseRepository",
    "DatabaseRepository",
    "get_database_repository",
    "PK",
    "Model",
)

from collections.abc import Callable
from collections.abc import Sequence
from typing import Generic
from typing import TypeVar

from fastapi import Depends
from otel import instrument
from sqlalchemy import ColumnExpressionArgument
from sqlalchemy import ScalarResult
from sqlalchemy import exists
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.interfaces import ORMOption
from sqlalchemy.sql.selectable import Select

from .database import Base
from .database import get_session

PK = TypeVar("PK")
Model = TypeVar("Model", bound=Base)

_original_filter = Select.filter


def _patched_filter(self, *expressions: ColumnExpressionArgument):
    """Patched filter method to use ansi (explicit) join syntax."""
    statement = self
    conditions = []
    for exp in expressions:
        if isinstance(exp, InstrumentedAttribute):  # relationship
            statement = statement.join(exp)
        else:
            conditions.append(exp)
    return _original_filter(statement, *conditions)


# Monkey-patch the Select.filter
Select.filter = _patched_filter


class BaseRepository:
    """Base repository class."""

    async def get(self, pk, **kwargs):
        raise NotImplementedError

    async def create(self, data):
        raise NotImplementedError

    async def update(self, instance, data):
        raise NotImplementedError

    async def delete(self, instance):
        raise NotImplementedError


@instrument
class DatabaseRepository(Generic[Model], BaseRepository):  # noqa: UP046
    """Defaul database repository"""

    subclasses = {}
    """Repository mapping, used to store each repository implementation."""

    def __init_subclass__(cls, model: type[Model] | None = None, **kwargs):
        if model:
            cls.subclasses[model] = cls
        super().__init_subclass__(**kwargs)

    def __init__(self, model: type[Model], session: AsyncSession, commit: bool = True):
        self.model = model
        self.session = session
        self.commit = commit

    async def get(self, pk: PK, **kwargs) -> Model | None:
        return await self.session.get(self.model, pk, **kwargs)

    async def get_by(self, **kwargs) -> Model | None:
        return (await self.filter_by(**kwargs)).one_or_none()

    async def create(self, **data) -> Model:
        instance = self.model(**data)
        self.session.add(instance)
        if self.commit:
            await self.session.commit()
        else:
            await self.session.flush()
        return instance

    async def update(self, instance: Model, **data) -> Model:
        for key, value in data.items():
            setattr(instance, key, value)
        if self.commit:
            await self.session.commit()
        else:
            await self.session.flush()
        return instance

    async def delete(self, instance: Model) -> None:
        await self.session.delete(instance)
        if self.commit:
            await self.session.commit()
        else:
            await self.session.flush()

    async def count(self, *expressions: ColumnExpressionArgument) -> int:
        statement = select(func.count(self.model.id))
        if expressions:
            statement = statement.filter(*expressions)
        return await self.session.scalar(statement)

    async def exists(self, *expressions: ColumnExpressionArgument) -> bool:
        statement = select(self.model.id)
        if expressions:
            statement = statement.filter(*expressions)
        return await self.session.scalar(select(exists(statement)))

    async def filter(
        self,
        *expressions: ColumnExpressionArgument,
        options: Sequence[ORMOption] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: list[str | ColumnExpressionArgument] | None = None,
    ) -> ScalarResult[Model]:
        statement = select(self.model)
        if expressions:
            statement = statement.filter(*expressions)
        if options:
            statement = statement.options(*options)
        if order_by:
            statement = statement.order_by(*order_by)
        if limit:
            statement = statement.limit(limit)
        if offset is not None:
            statement = statement.offset(offset)
        return await self.session.scalars(statement)

    async def filter_by(self, **kwargs) -> ScalarResult[Model]:
        options = kwargs.pop("options", None)
        statement = select(self.model).filter_by(**kwargs)
        if options:
            statement = statement.options(*options)
        return await self.session.scalars(statement)


@instrument
def get_database_repository(  # noqa: UP047
    model: type[Model],
    commit: bool = True,
) -> Callable[[AsyncSession], DatabaseRepository[Model]]:
    """Get model specific database repository dependency."""

    def func(session: AsyncSession = Depends(get_session)):
        repository = DatabaseRepository.subclasses.get(model, DatabaseRepository[model])
        return repository(model, session, commit)

    return func
