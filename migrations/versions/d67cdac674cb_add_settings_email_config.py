"""add settings email config

Revision ID: d67cdac674cb
Revises: b68b50a18b12
Create Date: 2026-01-11 13:44:52.808453

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd67cdac674cb'
down_revision = 'b68b50a18b12'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('settings', sa.Column('admin_notify_email', sa.String(length=120), nullable=True))
    op.add_column('settings', sa.Column('mail_server', sa.String(length=120), nullable=True))
    op.add_column('settings', sa.Column('mail_port', sa.Integer(), nullable=True))
    op.add_column('settings', sa.Column('mail_use_tls', sa.Boolean(), nullable=True))
    op.add_column('settings', sa.Column('mail_username', sa.String(length=120), nullable=True))
    op.add_column('settings', sa.Column('mail_password', sa.String(length=255), nullable=True))
    op.add_column('settings', sa.Column('mail_default_sender', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('settings', 'mail_default_sender')
    op.drop_column('settings', 'mail_password')
    op.drop_column('settings', 'mail_username')
    op.drop_column('settings', 'mail_use_tls')
    op.drop_column('settings', 'mail_port')
    op.drop_column('settings', 'mail_server')
    op.drop_column('settings', 'admin_notify_email')
