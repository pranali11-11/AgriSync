from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, DateTime, ForeignKey, Float, Boolean, Index, CheckConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(15), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="farmer", nullable=False)  # farmer | provider | admin
    language: Mapped[str] = mapped_column(String(5), default="en", nullable=False)  # en | hi | mr
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    farmer_profile: Mapped[Optional["FarmerProfile"]] = relationship(
        "FarmerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    provider_profile: Mapped[Optional["Provider"]] = relationship(
        "Provider", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    farms: Mapped[List["Farm"]] = relationship("Farm", back_populates="farmer", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class FarmerProfile(Base):
    __tablename__ = "farmer_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    village: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[Geography]] = mapped_column(
        Text().with_variant(Geography(geometry_type="POINT", srid=4326), "postgresql"), nullable=True
    )
    total_area_acres: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    __table_args__ = (
        Index("idx_farmer_profiles_location_gist", "location", postgresql_using="gist"),
        CheckConstraint("total_area_acres >= 0", name="chk_farmer_total_area_acres_non_negative"),
    )

    user: Mapped["User"] = relationship("User", back_populates="farmer_profile")


class Provider(Base):
    __tablename__ = "providers"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    org_type: Mapped[str] = mapped_column(String(20), default="owner", nullable=False)  # owner | FPO | CHC | service
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="provider_profile")
    machines: Mapped[List["Machine"]] = relationship("Machine", back_populates="provider", cascade="all, delete-orphan")
