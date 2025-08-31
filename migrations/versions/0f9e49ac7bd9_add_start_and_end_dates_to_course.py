"""Add start and end dates to Course"""

from alembic import op
import sqlalchemy as sa

revision = '0f9e49ac7bd9'
down_revision = '2491c86f1287'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('course', sa.Column('start_date', sa.DateTime(), nullable=True))
    op.add_column('course', sa.Column('end_date', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('course', 'end_date')
    op.drop_column('course', 'start_date')
