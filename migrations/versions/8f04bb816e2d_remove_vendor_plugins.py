"""

Revision ID: 8f04bb816e2d
Revises: 0e7a7c9bbdd1
Create Date: 2020-10-01 10:06:06.263072

"""

# revision identifiers, used by Alembic.
revision = '8f04bb816e2d'
down_revision = '0e7a7c9bbdd1'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('vendors', 'plugins')


def downgrade():
    op.add_column('vendors', sa.Column('plugins', sa.TEXT(), autoincrement=False, nullable=True))
