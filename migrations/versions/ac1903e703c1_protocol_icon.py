"""

Revision ID: ac1903e703c1
Revises: 8c854595b039
Create Date: 2020-11-10 20:40:17.910654

"""

# revision identifiers, used by Alembic.
revision = 'ac1903e703c1'
down_revision = '8c854595b039'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('protocol', sa.Column('icon', sa.Text(), nullable=True))
    op.add_column('categories', sa.Column('icon', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('protocol', 'icon')
    op.drop_column('categories', 'icon')
