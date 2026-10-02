from typing import List
from sqlalchemy import String, Boolean, Index, ARRAY, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geography
from app.core.database import Base


class InputSeller(Base):
    __tablename__ = "input_sellers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    location: Mapped[Geography] = mapped_column(
        Text().with_variant(Geography(geometry_type="POINT", srid=4326), "postgresql"), nullable=False
    )
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    categories: Mapped[List[str]] = mapped_column(
        JSON().with_variant(ARRAY(String(50)), "postgresql"), nullable=False
    )  # ['seeds', 'fertilizers', 'pesticides']

    __table_args__ = (
        Index("idx_input_sellers_location_gist", "location", postgresql_using="gist"),
    )
