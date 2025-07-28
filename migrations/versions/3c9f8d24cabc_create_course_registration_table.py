"""create course registration table

Revision ID: 3c9f8d24cabc
Revises: 50b7252785e9
Create Date: 2025-07-24 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3c9f8d24cabc'
down_revision = '50b7252785e9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'course_registration',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['course.id'])
    )


def downgrade():
    op.drop_table('course_registration')
