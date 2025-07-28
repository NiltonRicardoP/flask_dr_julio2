"""add server default to created_at columns

Revision ID: 481f6ea28bf5
Revises: aa1caddbd30a
Create Date: 2025-07-28 00:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = '481f6ea28bf5'
down_revision = 'aa1caddbd30a'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('course', 'created_at',
                    server_default=sa.func.now(),
                    existing_type=sa.DateTime())
    op.alter_column('course_registration', 'created_at',
                    server_default=sa.func.now(),
                    existing_type=sa.DateTime())


def downgrade():
    op.alter_column('course', 'created_at',
                    server_default=None,
                    existing_type=sa.DateTime())
    op.alter_column('course_registration', 'created_at',
                    server_default=None,
                    existing_type=sa.DateTime())
