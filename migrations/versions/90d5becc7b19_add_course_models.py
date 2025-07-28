"""add course models

Revision ID: 90d5becc7b19
Revises: c64b154fc459
Create Date: 2025-07-25 04:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '90d5becc7b19'
down_revision = 'c64b154fc459'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'course',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_table(
        'course_enrollment',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['course.id'])
    )


def downgrade():
    op.drop_table('course_enrollment')
    op.drop_table('course')
