"""drop ai tables

Revision ID: 9f3c3e9f2b12
Revises: d67cdac674cb
Create Date: 2026-01-11 15:05:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '9f3c3e9f2b12'
down_revision = 'd67cdac674cb'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP TABLE IF EXISTS ai_message")
    op.execute("DROP TABLE IF EXISTS ai_conversation")
    op.execute("DROP TABLE IF EXISTS ai_kb_entry")


def downgrade():
    pass
