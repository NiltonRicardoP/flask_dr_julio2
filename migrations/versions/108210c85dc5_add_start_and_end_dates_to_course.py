"""Add start and end dates to course

Revision ID: 108210c85dc5
Revises: 7221282e432a
Create Date: 2025-08-31 22:41:18.379513

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '108210c85dc5'
down_revision = '7221282e432a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('course', sa.Column('start_date', sa.DateTime(), nullable=True))
    op.add_column('course', sa.Column('end_date', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('course', 'end_date')
    op.drop_column('course', 'start_date')
