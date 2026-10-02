"""add machinery plan fields

Revision ID: 002_crop_machine_plan_fields
Revises: 001_initial_schema
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_crop_machine_plan_fields"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crop_machine_map", sa.Column("window_days", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("crop_machine_map", sa.Column("source", sa.Text(), nullable=False, server_default="SAMPLE - verify with ICAR / state agriculture dept"))


def downgrade() -> None:
    op.drop_column("crop_machine_map", "source")
    op.drop_column("crop_machine_map", "window_days")
