"""add google credentials storage

Revision ID: 6c8f4d2b1a10
Revises: c2f6a4d1a9b0
Create Date: 2026-03-13 23:50:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6c8f4d2b1a10"
down_revision = "c2f6a4d1a9b0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("settings", sa.Column("google_credentials_json", sa.Text(), nullable=True))
    op.add_column("settings", sa.Column("google_credentials_filename", sa.String(length=255), nullable=True))
    op.add_column("settings", sa.Column("google_credentials_uploaded_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("settings", "google_credentials_uploaded_at")
    op.drop_column("settings", "google_credentials_filename")
    op.drop_column("settings", "google_credentials_json")
