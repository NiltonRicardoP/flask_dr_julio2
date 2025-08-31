"""Add user_id to course_enrollment

Revision ID: bfbfdff3ce72
Revises: f1abe2984aa1
Create Date: 2025-08-31 22:40:52.690821

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bfbfdff3ce72'
down_revision = 'f1abe2984aa1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('course_enrollment') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_course_enrollment_user', 'user', ['user_id'], ['id'])


def downgrade():
    with op.batch_alter_table('course_enrollment') as batch_op:
        batch_op.drop_constraint('fk_course_enrollment_user', type_='foreignkey')
        batch_op.drop_column('user_id')
