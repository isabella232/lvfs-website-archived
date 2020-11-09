"""

Revision ID: 8c854595b039
Revises: 875766b17dda
Create Date: 2020-11-06 13:16:42.904943

"""

# revision identifiers, used by Alembic.
revision = '8c854595b039'
down_revision = '875766b17dda'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('components', sa.Column('icon', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('components', 'icon')
