"""add payment_method field to course_registration

Revision ID: b1f3c7d0a4c2
Revises: 481f6ea28bf5
Create Date: 2025-07-28 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = 'b1f3c7d0a4c2'
down_revision = '481f6ea28bf5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('course_registration', sa.Column('payment_method', sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column('course_registration', 'payment_method')
