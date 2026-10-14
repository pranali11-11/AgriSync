"""add government schemes and reminder subscriptions

Revision ID: 006_schemes_and_notifications
Revises: 005_irrigation_type_and_note
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "006_schemes_and_notifications"
down_revision: Union[str, None] = "005_irrigation_type_and_note"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("schemes"):
        op.create_table(
            "schemes",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("name_hi", sa.String(length=255), nullable=True),
            sa.Column("name_mr", sa.String(length=255), nullable=True),
            sa.Column("level", sa.String(length=20), nullable=False),
            sa.Column("department", sa.String(length=255), nullable=False),
            sa.Column("short_description", sa.Text(), nullable=False),
            sa.Column("short_description_hi", sa.Text(), nullable=True),
            sa.Column("short_description_mr", sa.Text(), nullable=True),
            sa.Column("eligibility_text", sa.Text(), nullable=False),
            sa.Column("benefits_text", sa.Text(), nullable=False),
            sa.Column("required_documents", postgresql.ARRAY(sa.Text()), nullable=False),
            sa.Column("application_process_text", sa.Text(), nullable=False),
            sa.Column("official_link", sa.String(length=500), nullable=False),
            sa.Column("deadline", sa.Date(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("crops", postgresql.ARRAY(sa.Text()), nullable=False),
            sa.Column("states", postgresql.ARRAY(sa.Text()), nullable=False),
            sa.Column("last_verified_on", sa.DateTime(), nullable=False),
            sa.Column("source", sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        existing_columns = {column["name"] for column in inspector.get_columns("schemes")}
        for column_name in ("short_description_hi", "short_description_mr"):
            if column_name not in existing_columns:
                op.add_column("schemes", sa.Column(column_name, sa.Text(), nullable=True))
        existing_types = {
            column["name"]: column["type"]
            for column in sa.inspect(bind).get_columns("schemes")
        }
        for column_name in ("required_documents", "crops", "states"):
            if not isinstance(existing_types[column_name], postgresql.ARRAY):
                temporary_name = f"{column_name}_text_array"
                op.add_column(
                    "schemes",
                    sa.Column(temporary_name, postgresql.ARRAY(sa.Text()), nullable=True),
                )
                op.execute(sa.text(
                    f"UPDATE schemes SET {temporary_name} = "
                    f"ARRAY(SELECT json_array_elements_text({column_name}))"
                ))
                op.alter_column("schemes", temporary_name, nullable=False)
                op.drop_column("schemes", column_name)
                op.alter_column("schemes", temporary_name, new_column_name=column_name)

    inspector = sa.inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("schemes")}
    for index_name, column_name in (
        ("ix_schemes_name", "name"),
        ("ix_schemes_level", "level"),
        ("ix_schemes_status", "status"),
    ):
        if index_name not in existing_indexes:
            op.create_index(index_name, "schemes", [column_name])

    inspector = sa.inspect(bind)
    if not inspector.has_table("scheme_notification_preferences"):
        op.create_table(
            "scheme_notification_preferences",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("scheme_id", sa.Integer(), nullable=False),
            sa.Column("subscribed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("notified_deadline", sa.Date(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["scheme_id"], ["schemes.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "scheme_id", name="uq_scheme_notification_user_scheme"),
        )
    inspector = sa.inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("scheme_notification_preferences")}
    for index_name, column_name in (
        ("ix_scheme_notification_preferences_user_id", "user_id"),
        ("ix_scheme_notification_preferences_scheme_id", "scheme_id"),
    ):
        if index_name not in existing_indexes:
            op.create_index(index_name, "scheme_notification_preferences", [column_name])


def downgrade() -> None:
    op.drop_index("ix_scheme_notification_preferences_scheme_id", table_name="scheme_notification_preferences")
    op.drop_index("ix_scheme_notification_preferences_user_id", table_name="scheme_notification_preferences")
    op.drop_table("scheme_notification_preferences")
    op.drop_index("ix_schemes_status", table_name="schemes")
    op.drop_index("ix_schemes_level", table_name="schemes")
    op.drop_index("ix_schemes_name", table_name="schemes")
    op.drop_table("schemes")
