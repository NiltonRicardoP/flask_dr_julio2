"""add access period to CourseEnrollment"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b6f3d6e3a6aa'
down_revision = 'f4797847a3d9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('course_enrollment', sa.Column('access_start', sa.DateTime(), nullable=True))
    op.add_column('course_enrollment', sa.Column('access_end', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('course_enrollment', 'access_end')
    op.drop_column('course_enrollment', 'access_start')
