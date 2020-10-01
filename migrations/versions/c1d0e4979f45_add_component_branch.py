"""

Revision ID: c1d0e4979f45
Revises: fbf18115ec00
Create Date: 2020-09-25 22:13:12.510991

"""

# revision identifiers, used by Alembic.
revision = 'c1d0e4979f45'
down_revision = 'fbf18115ec00'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('components', sa.Column('branch', sa.TEXT(), autoincrement=False, nullable=True))

def downgrade():
    op.drop_column('components', 'branch')
