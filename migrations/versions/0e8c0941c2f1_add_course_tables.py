"""Add course tables with additional fields

Revision ID: 0e8c0941c2f1
Revises: 90d5becc7b19
Create Date: 2025-07-25 04:05:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0e8c0941c2f1'
down_revision = '90d5becc7b19'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'course',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image', sa.String(length=255), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('access_url', sa.String(length=255), nullable=True),
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
        sa.Column('payment_status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['course.id'])
    )


def downgrade():
    op.drop_table('course_enrollment')
    op.drop_table('course')
