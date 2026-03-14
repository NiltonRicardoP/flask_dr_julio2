"""make appointment email nullable

Revision ID: b68b50a18b12
Revises: 2dc3c1741a94
Create Date: 2025-12-07 15:04:37.743942

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b68b50a18b12'
down_revision = '2dc3c1741a94'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "appointment",
        "email",
        existing_type=sa.String(length=100),
        nullable=True
    )

def downgrade():
    op.alter_column(
        "appointment",
        "email",
        existing_type=sa.String(length=100),
        nullable=False
    )
