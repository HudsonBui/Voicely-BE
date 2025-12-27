from sqlalchemy.sql import func

from app.models.base_import import (
    Base,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    relationship,
)


class UserDevice(Base):
    __tablename__ = "user_devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    fcm_token = Column(String, unique=True, nullable=False, index=True)
    device_type = Column(String, nullable=True)
    device_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, default=func.now(), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="devices")
