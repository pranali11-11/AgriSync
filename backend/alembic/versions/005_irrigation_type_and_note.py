"""add irrigation_type_note and migrate legacy irrigation values

Revision ID: 005_irrigation_type_and_note
Revises: 004_crop_category
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005_irrigation_type_and_note"
down_revision: Union[str, None] = "004_crop_category"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add irrigation_type_note column
    op.add_column("farms", sa.Column("irrigation_type_note", sa.Text(), nullable=True))

    # 2. Data migration for legacy irrigation values
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE farms SET irrigation_type = 'well' WHERE LOWER(irrigation_type) = 'well'"))
    bind.execute(sa.text("UPDATE farms SET irrigation_type = 'canal' WHERE LOWER(irrigation_type) = 'canal'"))
    bind.execute(sa.text("UPDATE farms SET irrigation_type = 'drip' WHERE LOWER(irrigation_type) = 'drip' OR LOWER(irrigation_type) LIKE '%drip%'"))
    bind.execute(sa.text("UPDATE farms SET irrigation_type = 'borewell' WHERE LOWER(irrigation_type) = 'borewell'"))
    bind.execute(sa.text("UPDATE farms SET irrigation_type = 'rainfed' WHERE LOWER(irrigation_type) = 'rainfed'"))
    bind.execute(sa.text("UPDATE farms SET irrigation_type = 'sprinkler' WHERE LOWER(irrigation_type) = 'sprinkler'"))
    bind.execute(sa.text("UPDATE farms SET irrigation_type = 'pond_tank' WHERE LOWER(irrigation_type) IN ('pond', 'tank', 'pond/tank', 'pond_tank')"))


def downgrade() -> None:
    op.drop_column("farms", "irrigation_type_note")
