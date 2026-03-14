"""add calendar events

Revision ID: c2f6a4d1a9b0
Revises: 5a1b2c3d4e5f
Create Date: 2026-01-26 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c2f6a4d1a9b0"
down_revision = "5a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "calendar_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column("end_at", sa.DateTime(), nullable=False),
        sa.Column("all_day", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.Column("google_event_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_calendar_event_google_event_id",
        "calendar_event",
        ["google_event_id"],
        unique=True,
    )


def downgrade():
    op.drop_index("ix_calendar_event_google_event_id", table_name="calendar_event")
    op.drop_table("calendar_event")
