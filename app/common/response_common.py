from typing import Any, Optional
from fastapi import status


class ResponseCommon:
    def __init__(
        self,
        code: int = status.HTTP_200_OK,
        success: bool = True,
        message: str = "",
        data: Optional[Any] = None,
    ):
        self.success = success
        self.message = message
        self.data = data
        self.code = code

    def to_json(self) -> dict:
        return {
            "code": self.code,
            "success": self.success,
            "message": self.message,
            "data": self.data,
        }

    def to_json_data(self) -> dict:
        return {
            "message": self.message,
            "data": self.data,
        }

    @classmethod
    def success_response(
        cls, data: Optional[Any] = None, message: str = "", code: int = status.HTTP_200_OK
    ) -> "ResponseCommon":
        return cls(code=code, success=True, message=message, data=data)

    @classmethod
    def error_response(
        cls, message: str, code: int = status.HTTP_400_BAD_REQUEST, data: Optional[Any] = None
    ) -> "ResponseCommon":
        return cls(code=code, success=False, message=message, data=data)
