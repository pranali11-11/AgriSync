"""add crop category

Revision ID: 004_crop_category
Revises: 003_group_metadata
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004_crop_category"
down_revision: Union[str, None] = "003_group_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crops", sa.Column("category", sa.String(length=50), nullable=False, server_default="other"))
    op.create_index(op.f("ix_crops_category"), "crops", ["category"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_crops_category"), table_name="crops")
    op.drop_column("crops", "category")
