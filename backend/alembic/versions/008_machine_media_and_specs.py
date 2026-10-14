"""008_machine_media_and_specs

Revision ID: 008
Revises: 007
Create Date: 2026-10-07

Adds four new nullable columns to the machines table:
  - photos        JSON array of public photo URLs
  - description   free-text description
  - model_year    integer (e.g. 2021)
  - specifications JSON object (e.g. {"horsepower": 45, "attachments": ["rotavator"]})
Also adds mobilization_cost column (float, default 0) to machines.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "008"
down_revision = "007_crop_stage_desc_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add rich-listing columns to machines table
    with op.batch_alter_table("machines") as batch_op:
        batch_op.add_column(sa.Column("mobilization_cost", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("photos", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("model_year", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("specifications", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("machines") as batch_op:
        batch_op.drop_column("specifications")
        batch_op.drop_column("model_year")
        batch_op.drop_column("description")
        batch_op.drop_column("photos")
        batch_op.drop_column("mobilization_cost")
