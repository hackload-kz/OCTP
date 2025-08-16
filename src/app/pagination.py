from otel import instrument

from app.middlewares import request_context
from app.schemas import PaginatedResponse
from app.schemas import T


@instrument
def paginated_response(
    results: list[T],
    count: int,
    limit: int,
    offset: int,
) -> PaginatedResponse[T]:
    """Get a PaginatedResponse with next/previous links"""
    request = request_context.get()

    next_url = None
    next_offset = offset + limit
    if next_offset < count:
        next_url = str(
            request.url.replace_query_params(offset=next_offset, limit=limit)
        )

    prev_url = None
    prev_offset = offset - limit
    if prev_offset >= 0:
        prev_url = str(
            request.url.replace_query_params(offset=prev_offset, limit=limit)
        )

    return PaginatedResponse[T](
        count=count,
        next=next_url,
        previous=prev_url,
        results=results,
    )
