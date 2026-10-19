from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.enums import RoleEnum
from app.timestamps import Timestamps


class User(Timestamps, Base):
    """Prasang profile of a SuperTokens user. `id` is the SuperTokens user id."""

    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(10))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(RoleEnum)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
