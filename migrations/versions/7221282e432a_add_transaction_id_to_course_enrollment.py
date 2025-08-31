"""Add transaction_id to course_enrollment

Revision ID: 7221282e432a
Revises: c20481b97df5
Create Date: 2025-08-31 22:41:10.021687

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7221282e432a'
down_revision = 'c20481b97df5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('course_enrollment', sa.Column('transaction_id', sa.String(length=100), nullable=True))


def downgrade():
    op.drop_column('course_enrollment', 'transaction_id')
