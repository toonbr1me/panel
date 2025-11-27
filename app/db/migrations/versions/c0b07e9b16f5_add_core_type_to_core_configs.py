"""add core_type to core_configs

Revision ID: c0b07e9b16f5
Revises: a0a1125e46b1
Create Date: 2025-01-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c0b07e9b16f5'
down_revision = 'a0a1125e46b1'
branch_labels = None
depends_on = None


core_type_enum = sa.Enum('xray', 'sing_box', name='coretype')

def upgrade() -> None:
    bind = op.get_bind()
    core_type_enum.create(bind, checkfirst=True)
    op.add_column(
        'core_configs',
        sa.Column('core_type', core_type_enum, nullable=False, server_default='xray'),
    )
    op.execute("UPDATE core_configs SET core_type = 'xray' WHERE core_type IS NULL")


def downgrade() -> None:
    op.drop_column('core_configs', 'core_type')
    bind = op.get_bind()
    core_type_enum.drop(bind, checkfirst=True)
