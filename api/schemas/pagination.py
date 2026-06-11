"""Generic pagination envelope for list endpoints.

§6 — API pagination convention (v4.11): list endpoints return
{items, total, limit, offset} so clients can render page controls.
"""

from pydantic import BaseModel


class Page[T](BaseModel):
    """Paginated response envelope."""

    items: list[T]
    total: int
    limit: int
    offset: int
