from datetime import date, datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import String, Date, ForeignKey, Float, CheckConstraint, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class IrrigationType(str, Enum):
    """Canonical irrigation method values stored in farms.irrigation_type."""
    rainfed   = "rainfed"
    canal     = "canal"
    borewell  = "borewell"
    well      = "well"
    drip      = "drip"
    sprinkler = "sprinkler"
    pond_tank = "pond_tank"
    other     = "other"

    # Legacy aliases produced by the old 4-option UI and variants
    @classmethod
    def _missing_(cls, value: object):
        """Gracefully map old free-text values and variants to canonical enum members."""
        if not isinstance(value, str):
            return None
        cleaned = value.strip().lower()
        mapping = {
            "drip / sprinkler": cls.drip,
            "drip/sprinkler":   cls.drip,
            "sprinkler":        cls.sprinkler,
            "tank":             cls.pond_tank,
            "pond":             cls.pond_tank,
            "pond/tank":        cls.pond_tank,
            "pond / tank":      cls.pond_tank,
            "pond_tank":        cls.pond_tank,
        }
        if cleaned in mapping:
            return mapping[cleaned]
        for member in cls:
            if member.value == cleaned:
                return member
        return None


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id", ondelete="RESTRICT"), index=True, nullable=False)
    sowing_date: Mapped[date] = mapped_column(Date, nullable=False)
    area_acres: Mapped[float] = mapped_column(Float, nullable=False)
    soil_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Black, Clay, Loam, Sandy
    current_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    irrigation_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # IrrigationType enum value
    irrigation_type_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Free-text when type='other'

    __table_args__ = (
        CheckConstraint("area_acres > 0", name="chk_farm_area_acres_positive"),
    )

    farmer: Mapped["User"] = relationship("User", back_populates="farms")
    crop: Mapped["Crop"] = relationship("Crop", back_populates="farms")
    soil_tests: Mapped[List["SoilTest"]] = relationship("SoilTest", back_populates="farm", cascade="all, delete-orphan")
    fertilizer_records: Mapped[List["FertilizerHistory"]] = relationship("FertilizerHistory", back_populates="farm", cascade="all, delete-orphan")
    group_memberships: Mapped[List["GroupMember"]] = relationship("GroupMember", back_populates="farm")


class SoilTest(Base):
    __tablename__ = "soil_tests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), index=True, nullable=False)
    ph: Mapped[float] = mapped_column(Float, nullable=False)
    nitrogen: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    phosphorus: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    potassium: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    organic_carbon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tested_on: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        CheckConstraint("ph >= 0 AND ph <= 14", name="chk_soil_ph_valid_range"),
    )

    farm: Mapped["Farm"] = relationship("Farm", back_populates="soil_tests")


class FertilizerHistory(Base):
    __tablename__ = "fertilizer_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), index=True, nullable=False)
    product_category: Mapped[str] = mapped_column(String(100), nullable=False)  # Urea, DAP, NPK, Compost
    applied_on: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="chk_fertilizer_quantity_positive"),
    )

    farm: Mapped["Farm"] = relationship("Farm", back_populates="fertilizer_records")
