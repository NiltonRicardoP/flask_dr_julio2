"""Add patients and appointment manage tokens.

Revision ID: 4f2a9e3c1b17
Revises: 3c4b8d2e7f11
Create Date: 2026-01-11 22:05:00
"""

from alembic import op
import sqlalchemy as sa


revision = "4f2a9e3c1b17"
down_revision = "3c4b8d2e7f11"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("appointment", sa.Column("manage_token", sa.String(length=64), nullable=True))
    op.add_column("appointment", sa.Column("cancelled_at", sa.DateTime(), nullable=True))
    op.add_column("appointment", sa.Column("rescheduled_at", sa.DateTime(), nullable=True))
    op.add_column("appointment", sa.Column("reminder_sent_at", sa.DateTime(), nullable=True))
    op.create_index("ix_appointment_manage_token", "appointment", ["manage_token"], unique=True)

    op.create_table(
        "patient",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=120)),
        sa.Column("phone", sa.String(length=30)),
        sa.Column("birth_date", sa.Date()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    op.create_table(
        "patient_note",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("title", sa.String(length=150)),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )


def downgrade():
    op.drop_table("patient_note")
    op.drop_table("patient")

    op.drop_index("ix_appointment_manage_token", table_name="appointment")
    op.drop_column("appointment", "reminder_sent_at")
    op.drop_column("appointment", "rescheduled_at")
    op.drop_column("appointment", "cancelled_at")
    op.drop_column("appointment", "manage_token")
