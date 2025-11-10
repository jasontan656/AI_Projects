from __future__ import annotations

"""Standard API response envelope."""

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int
    pageSize: int = Field(alias="pageSize")
    total: int

    model_config = {"populate_by_name": True}


class ApiMeta(BaseModel):
    request_id: str = Field(alias="requestId")
    pagination: Optional[PaginationMeta] = None
    warnings: List[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class ApiError(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel, Generic[T]):
    data: Optional[T]
    meta: ApiMeta
    errors: List[ApiError] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
