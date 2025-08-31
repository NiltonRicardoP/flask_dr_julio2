from alembic import op
import sqlalchemy as sa

revision = 'add_role_to_user'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('user', sa.Column('role', sa.String(length=20), server_default='student', nullable=True))
    op.execute("UPDATE ""user"" SET role='student' WHERE role IS NULL")


def downgrade():
    op.drop_column('user', 'role')
