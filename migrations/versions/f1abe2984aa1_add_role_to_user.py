"""Add role to user

Revision ID: f1abe2984aa1
Revises: eb317f28979a
Create Date: 2025-08-31 22:40:45.107092

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1abe2984aa1'
down_revision = 'eb317f28979a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('role', sa.String(length=20), nullable=True))


def downgrade():
    op.drop_column('user', 'role')
