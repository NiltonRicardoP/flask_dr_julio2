"""add payment fields to course registration

Revision ID: aa1caddbd30a
Revises: 733c67a962d6
Create Date: 2025-07-28 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = 'aa1caddbd30a'
down_revision = '733c67a962d6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('course_registration', sa.Column('payment_status', sa.String(length=20), nullable=True))
    op.add_column('course_registration', sa.Column('transaction_id', sa.String(length=100), nullable=True))


def downgrade():
    op.drop_column('course_registration', 'transaction_id')
    op.drop_column('course_registration', 'payment_status')
