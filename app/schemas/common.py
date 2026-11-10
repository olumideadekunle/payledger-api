from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[T] = None


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    limit: int
    offset: int
    items: List[T]


class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
