from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.session import Base