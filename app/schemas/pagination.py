from enum import Enum
from typing import Optional, List, TypeVar, Generic

from pydantic import BaseModel, Field


class SortOrder(str, Enum):
    """Sort order enumeration"""

    ASC = "ASC"
    DESC = "DESC"


class PageOptionsDto(BaseModel):
    """
    Base pagination and filtering options.
    All list/search endpoints should extend this class.
    """

    page: int = Field(default=1, ge=1, description="Current page number (starts at 1)")
    page_size: int = Field(default=10, ge=1, le=100, description="Number of items per page")
    order: SortOrder = Field(default=SortOrder.DESC, description="Sort order (ASC or DESC)")
    search: Optional[str] = Field(default=None, description="General search keyword")
    is_dropdown: bool = Field(default=False, description="If true, return all items without pagination")

    class Config:
        use_enum_values = True


class PageMetaDto(BaseModel):
    """
    Pagination metadata returned with paginated responses
    """

    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    item_count: int = Field(..., description="Total items matching filters")
    page_count: int = Field(..., description="Total number of pages")
    has_previous_page: bool = Field(..., description="Whether there is a previous page")
    has_next_page: bool = Field(..., description="Whether there is a next page")


T = TypeVar("T")


class PageDto(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper
    """

    data: List[T] = Field(..., description="Array of items for current page")
    meta: PageMetaDto = Field(..., description="Pagination metadata")


class ResponseCommon(BaseModel, Generic[T]):
    """
    Standard API response wrapper
    """

    code: int = Field(default=200, description="HTTP status code")
    success: bool = Field(default=True, description="Whether request was successful")
    message: str = Field(default="SUCCESSFULLY", description="Response message")
    data: Optional[T] = Field(default=None, description="Response data")
