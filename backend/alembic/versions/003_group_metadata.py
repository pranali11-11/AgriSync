"""add group discovery metadata

Revision ID: 003_group_metadata
Revises: 002_crop_machine_plan_fields
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003_group_metadata"
down_revision: Union[str, None] = "002_crop_machine_plan_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("booking_groups", sa.Column("name", sa.String(length=150), nullable=True))
    op.add_column("booking_groups", sa.Column("description", sa.String(length=500), nullable=True))
    op.add_column("booking_groups", sa.Column("crop_focus", sa.String(length=100), nullable=True))
    op.add_column("booking_groups", sa.Column("radius_km", sa.Float(), nullable=False, server_default="10"))


def downgrade() -> None:
    op.drop_column("booking_groups", "radius_km")
    op.drop_column("booking_groups", "crop_focus")
    op.drop_column("booking_groups", "description")
    op.drop_column("booking_groups", "name")