"""Add transaction_id to CourseEnrollment"""

from alembic import op
import sqlalchemy as sa

revision = '2491c86f1287'
down_revision = 'b6f3d6e3a6aa'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('course_enrollment', sa.Column('transaction_id', sa.String(length=100), nullable=True))


def downgrade():
    op.drop_column('course_enrollment', 'transaction_id')
