from fastapi import APIRouter, Depends
from app.api.deps import get_current_active_user
from app.models import User

router = APIRouter()

@router.get("/users/me")
def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user