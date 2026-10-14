from datetime import date
from typing import Optional, List, Any
from sqlalchemy import String, Integer, ForeignKey, Float, Boolean, Date, Index, CheckConstraint, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography
from app.core.database import Base


class MachineType(Base):
    __tablename__ = "machine_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name_hi: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    name_mr: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    typical_rate_per_acre: Mapped[float] = mapped_column(Float, nullable=False)
    mobilization_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    machines: Mapped[List["Machine"]] = relationship("Machine", back_populates="machine_type")
    crop_mappings: Mapped[List["CropMachineMap"]] = relationship("CropMachineMap", back_populates="machine_type")


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.user_id", ondelete="CASCADE"), index=True, nullable=False)
    machine_type_id: Mapped[int] = mapped_column(ForeignKey("machine_types.id", ondelete="RESTRICT"), index=True, nullable=False)
    location: Mapped[Geography] = mapped_column(
        Text().with_variant(Geography(geometry_type="POINT", srid=4326), "postgresql"), nullable=False
    )
    rate_per_acre: Mapped[float] = mapped_column(Float, nullable=False)
    mobilization_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    available_from: Mapped[date] = mapped_column(Date, nullable=False)
    available_to: Mapped[date] = mapped_column(Date, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rating: Mapped[float] = mapped_column(Float, default=4.5, nullable=False)

    # Rich listing fields added in Stage A
    photos: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)          # list[str] of public photo URLs
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    specifications: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)  # e.g. {"horsepower": 45, "attachments": ["rotavator"]}

    __table_args__ = (
        Index("idx_machines_location_gist", "location", postgresql_using="gist"),
        CheckConstraint("rate_per_acre > 0", name="chk_machine_rate_positive"),
        CheckConstraint("rating >= 0 AND rating <= 5", name="chk_machine_rating_range"),
    )

    provider: Mapped["Provider"] = relationship("Provider", back_populates="machines")
    machine_type: Mapped["MachineType"] = relationship("MachineType", back_populates="machines")
    booking_groups: Mapped[List["BookingGroup"]] = relationship("BookingGroup", back_populates="machine")


class CropMachineMap(Base):
    __tablename__ = "crop_machine_map"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id", ondelete="CASCADE"), index=True, nullable=False)
    stage_id: Mapped[Optional[int]] = mapped_column(ForeignKey("crop_stages.id", ondelete="SET NULL"), nullable=True)
    machine_type_id: Mapped[int] = mapped_column(ForeignKey("machine_types.id", ondelete="CASCADE"), index=True, nullable=False)
    days_offset: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    window_days: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    source: Mapped[str] = mapped_column(String(255), default="SAMPLE - verify with ICAR / state agriculture dept", nullable=False)

    crop: Mapped["Crop"] = relationship("Crop", back_populates="machine_mappings")
    stage: Mapped[Optional["CropStage"]] = relationship("CropStage", back_populates="machine_mappings")
    machine_type: Mapped["MachineType"] = relationship("MachineType", back_populates="crop_mappings")
