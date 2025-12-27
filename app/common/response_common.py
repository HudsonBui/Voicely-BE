from typing import Any, Optional, TypeVar

from fastapi import status
from fastapi.encoders import jsonable_encoder

from app.schemas.pagination import ResponseCommon as ResponseCommonSchema

T = TypeVar("T")


def create_success_response(
    data: Optional[T] = None, message: str = "SUCCESSFULLY", code: int = status.HTTP_200_OK
) -> "ResponseCommon":
    """Create a successful response"""
    return ResponseCommon(code=code, success=True, message=message, data=data)


def create_error_response(
    message: str, code: int = status.HTTP_400_BAD_REQUEST, data: Optional[T] = None
) -> "ResponseCommon":
    """Create an error response"""
    return ResponseCommon(code=code, success=False, message=message, data=data)


class ResponseCommon(ResponseCommonSchema):
    data: Optional[Any] = None

    def to_json(self) -> dict:
        return jsonable_encoder(self)

    def to_json_data(self) -> dict:
        return jsonable_encoder({"message": self.message, "data": self.data})

    @classmethod
    def success_response(
        cls,
        data: Optional[Any] = None,
        message: str = "SUCCESSFULLY",
        code: int = status.HTTP_200_OK,
    ) -> "ResponseCommon":
        return cls(code=code, success=True, message=message, data=data)

    @classmethod
    def error_response(
        cls,
        message: str,
        code: int = status.HTTP_400_BAD_REQUEST,
        data: Optional[Any] = None,
    ) -> "ResponseCommon":
        return cls(code=code, success=False, message=message, data=data)
