from datetime import date
from typing import Optional, List
from sqlalchemy import String, Integer, ForeignKey, Float, Date, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class BookingGroup(Base):
    __tablename__ = "booking_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id", ondelete="RESTRICT"), index=True, nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)  # open | confirmed | completed | cancelled
    min_farmers: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    max_acres: Mapped[float] = mapped_column(Float, default=20.0, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    crop_focus: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    radius_km: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)

    __table_args__ = (
        CheckConstraint("min_farmers > 0", name="chk_group_min_farmers_positive"),
        CheckConstraint("max_acres > 0", name="chk_group_max_acres_positive"),
    )

    machine: Mapped["Machine"] = relationship("Machine", back_populates="booking_groups")
    creator: Mapped["User"] = relationship("User")
    members: Mapped[List["GroupMember"]] = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("booking_groups.id", ondelete="CASCADE"), index=True, nullable=False)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id", ondelete="RESTRICT"), index=True, nullable=False)
    acres: Mapped[float] = mapped_column(Float, nullable=False)
    share_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="joined", nullable=False)  # joined | paid | cancelled

    __table_args__ = (
        UniqueConstraint("group_id", "farmer_id", name="uq_group_members_group_farmer"),
        CheckConstraint("acres > 0", name="chk_group_member_acres_positive"),
        CheckConstraint("share_amount >= 0", name="chk_group_member_share_non_negative"),
    )

    group: Mapped["BookingGroup"] = relationship("BookingGroup", back_populates="members")
    farmer: Mapped["User"] = relationship("User")
    farm: Mapped["Farm"] = relationship("Farm", back_populates="group_memberships")
