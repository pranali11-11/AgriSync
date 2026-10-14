from typing import Optional, List, Dict, Any
from sqlalchemy import ARRAY, String, Text, JSON, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date, datetime, timezone
from app.core.database import Base


class Scheme(Base):
    __tablename__ = "schemes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name_hi: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    name_mr: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # central | state
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    short_description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description_hi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_description_mr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    eligibility_text: Mapped[str] = mapped_column(Text, nullable=False)
    benefits_text: Mapped[str] = mapped_column(Text, nullable=False)
    required_documents: Mapped[List[str]] = mapped_column(
        ARRAY(Text).with_variant(JSON, "sqlite"), nullable=False, default=list
    )
    application_process_text: Mapped[str] = mapped_column(Text, nullable=False)
    official_link: Mapped[str] = mapped_column(String(500), nullable=False)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)  # active | upcoming | closed
    crops: Mapped[List[str]] = mapped_column(
        ARRAY(Text).with_variant(JSON, "sqlite"), nullable=False, default=list
    )
    states: Mapped[List[str]] = mapped_column(
        ARRAY(Text).with_variant(JSON, "sqlite"), nullable=False, default=list
    )
    last_verified_on: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)


class SchemeNotificationPreference(Base):
    __tablename__ = "scheme_notification_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id", ondelete="CASCADE"), index=True, nullable=False)
    subscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    notified_deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "scheme_id", name="uq_scheme_notification_user_scheme"),
    )
