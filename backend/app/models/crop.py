from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Crop(Base):
    __tablename__ = "crops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name_hi: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    name_mr: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="other", index=True)

    stages: Mapped[List["CropStage"]] = relationship(
        "CropStage", back_populates="crop", cascade="all, delete-orphan", order_by="CropStage.start_day"
    )
    farms: Mapped[List["Farm"]] = relationship("Farm", back_populates="crop")
    nutrient_rules: Mapped[List["NutrientRule"]] = relationship("NutrientRule", back_populates="crop")
    machine_mappings: Mapped[List["CropMachineMap"]] = relationship("CropMachineMap", back_populates="crop")


class CropStage(Base):
    __tablename__ = "crop_stages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id", ondelete="CASCADE"), index=True, nullable=False)
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_day: Mapped[int] = mapped_column(Integer, nullable=False)
    end_day: Mapped[int] = mapped_column(Integer, nullable=False)

    crop: Mapped["Crop"] = relationship("Crop", back_populates="stages")
    nutrient_rules: Mapped[List["NutrientRule"]] = relationship("NutrientRule", back_populates="stage")
    machine_mappings: Mapped[List["CropMachineMap"]] = relationship("CropMachineMap", back_populates="stage")


class NutrientRule(Base):
    __tablename__ = "nutrient_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id", ondelete="CASCADE"), index=True, nullable=False)
    stage_id: Mapped[Optional[int]] = mapped_column(ForeignKey("crop_stages.id", ondelete="SET NULL"), nullable=True)
    nutrient: Mapped[str] = mapped_column(String(50), nullable=False)  # N, P, K, pH, Organic Carbon, etc.
    condition_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    guidance_text: Mapped[str] = mapped_column(Text, nullable=False)
    input_category: Mapped[str] = mapped_column(String(50), nullable=False)  # Fertilizer, Organic, Irrigation
    source: Mapped[str] = mapped_column(
        String(255),
        default="SAMPLE - verify with ICAR / state agriculture dept",
        nullable=False
    )

    crop: Mapped["Crop"] = relationship("Crop", back_populates="nutrient_rules")
    stage: Mapped[Optional["CropStage"]] = relationship("CropStage", back_populates="nutrient_rules")
