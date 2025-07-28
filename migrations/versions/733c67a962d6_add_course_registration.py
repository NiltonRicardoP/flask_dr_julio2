"""add course registration and payment tables

Revision ID: 733c67a962d6
Revises: 0e8c0941c2f1
Create Date: 2025-07-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '733c67a962d6'
down_revision = '0e8c0941c2f1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'course_registration',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('participant_name', sa.String(length=100), nullable=False),
        sa.Column('participant_email', sa.String(length=100), nullable=False),
        sa.Column('payment_status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['course.id'])
    )
    op.create_table(
        'payment',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('registration_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('transaction_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['registration_id'], ['course_registration.id'])
    )


def downgrade():
    op.drop_table('payment')
    op.drop_table('course_registration')
