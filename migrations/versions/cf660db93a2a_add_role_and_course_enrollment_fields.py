"""add role and course enrollment fields

Revision ID: cf660db93a2a
Revises: d87de128377f
Create Date: 2025-09-01 01:15:22.676908
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'cf660db93a2a'
down_revision = 'd87de128377f'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    # 1) Adiciona user.role se não existir (com default 'student')
    if 'user' in insp.get_table_names():
        user_cols = {c['name'] for c in insp.get_columns('user')}
        if 'role' not in user_cols:
            # server_default garante preenchimento para linhas existentes no SQLite
            with op.batch_alter_table('user') as batch:
                batch.add_column(sa.Column('role', sa.String(length=20), nullable=False, server_default='student'))

    # 2) course_enrollment:
    #    - se não existir, cria a tabela completa (com FKs)
    #    - se existir, adiciona as colunas que faltarem (modo batch)
    if 'course_enrollment' not in insp.get_table_names():
        op.create_table(
            'course_enrollment',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('course_id', sa.Integer, sa.ForeignKey('course.id'), nullable=False),
            sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id'), nullable=False),
            sa.Column('transaction_id', sa.String(length=100)),
            sa.Column('created_at', sa.DateTime),
        )
    else:
        ce_cols = {c['name'] for c in insp.get_columns('course_enrollment')}
        with op.batch_alter_table('course_enrollment') as batch:
            if 'course_id' not in ce_cols:
                batch.add_column(sa.Column('course_id', sa.Integer(), nullable=False))
            if 'user_id' not in ce_cols:
                batch.add_column(sa.Column('user_id', sa.Integer(), nullable=False))
            if 'transaction_id' not in ce_cols:
                batch.add_column(sa.Column('transaction_id', sa.String(length=100)))
            if 'created_at' not in ce_cols:
                batch.add_column(sa.Column('created_at', sa.DateTime()))


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    if 'course_enrollment' in insp.get_table_names():
        ce_cols = {c['name'] for c in insp.get_columns('course_enrollment')}
        with op.batch_alter_table('course_enrollment') as batch:
            for col in ['created_at', 'transaction_id', 'user_id', 'course_id']:
                if col in ce_cols:
                    batch.drop_column(col)

    if 'user' in insp.get_table_names():
        user_cols = {c['name'] for c in insp.get_columns('user')}
        if 'role' in user_cols:
            with op.batch_alter_table('user') as batch:
                batch.drop_column('role')
