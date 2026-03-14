"""Add Google Calendar sync fields.

Revision ID: 5a1b2c3d4e5f
Revises: 4f2a9e3c1b17
Create Date: 2026-01-12 10:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "5a1b2c3d4e5f"
down_revision = "4f2a9e3c1b17"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("appointment", sa.Column("google_event_id", sa.String(length=128), nullable=True))
    op.create_index("ix_appointment_google_event_id", "appointment", ["google_event_id"], unique=False)

    op.add_column("settings", sa.Column("google_calendar_id", sa.String(length=255), nullable=True))
    op.add_column("settings", sa.Column("google_attendee_emails", sa.Text(), nullable=True))
    op.add_column("settings", sa.Column("google_sync_enabled", sa.Boolean(), nullable=True))
    op.add_column("settings", sa.Column("google_sync_token", sa.Text(), nullable=True))
    op.add_column("settings", sa.Column("google_sync_last_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("settings", "google_sync_last_at")
    op.drop_column("settings", "google_sync_token")
    op.drop_column("settings", "google_sync_enabled")
    op.drop_column("settings", "google_attendee_emails")
    op.drop_column("settings", "google_calendar_id")

    op.drop_index("ix_appointment_google_event_id", table_name="appointment")
    op.drop_column("appointment", "google_event_id")
