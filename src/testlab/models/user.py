# Здесь будут модели данных таблицы users

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column
from testlab.database import Base
from testlab.schemas.user import UserRole

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), default=UserRole.student, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)