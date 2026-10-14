"""add stage_description and source to crop_stages

Revision ID: 007_crop_stage_description_and_source
Revises: 006_schemes_and_notifications
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision = "007_crop_stage_desc_source"
down_revision: Union[str, None] = "006_schemes_and_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crop_stages", sa.Column("stage_description", sa.Text(), nullable=True))
    op.add_column(
        "crop_stages",
        sa.Column(
            "source",
            sa.String(length=255),
            nullable=False,
            server_default="SAMPLE - verify with ICAR / state agriculture dept",
        ),
    )


def downgrade() -> None:
    op.drop_column("crop_stages", "source")
    op.drop_column("crop_stages", "stage_description")
