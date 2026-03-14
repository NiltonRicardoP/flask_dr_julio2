"""add site sections

Revision ID: 3c4b8d2e7f11
Revises: 9f3c3e9f2b12
Create Date: 2026-01-11 22:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c4b8d2e7f11'
down_revision = '9f3c3e9f2b12'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'site_section',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('page', sa.String(length=50), nullable=False),
        sa.Column('slug', sa.String(length=60), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=True),
        sa.Column('subtitle', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.UniqueConstraint('slug'),
    )
    op.create_table(
        'site_section_item',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('section_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['section_id'], ['site_section.id']),
    )


def downgrade():
    op.drop_table('site_section_item')
    op.drop_table('site_section')
