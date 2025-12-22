from fastapi import APIRouter, Depends
from app.api.deps import get_current_active_user
from app.models import User
from app.common.response_common import ResponseCommon
from app.common.common_message import CommonMessage

router = APIRouter()

@router.get("/users/me")
def read_users_me(current_user: User = Depends(get_current_active_user)):
    response = ResponseCommon.success_response(
        data={
            "id": current_user.id,
            "email": current_user.email,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at
        },
        message=CommonMessage.USER_INFO_RETRIEVED_SUCCESS
    )
    return response.to_json()