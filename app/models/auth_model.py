
from app.models.base_import import BaseModel, EmailStr


class AuthModel(BaseModel):
    email: EmailStr
    password: str