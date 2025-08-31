"""Add access period to course_enrollment

Revision ID: c20481b97df5
Revises: bfbfdff3ce72
Create Date: 2025-08-31 22:41:01.322309

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c20481b97df5'
down_revision = 'bfbfdff3ce72'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('course_enrollment', sa.Column('access_start', sa.DateTime(), nullable=True))
    op.add_column('course_enrollment', sa.Column('access_end', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('course_enrollment', 'access_end')
    op.drop_column('course_enrollment', 'access_start')
