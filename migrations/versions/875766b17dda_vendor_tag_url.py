"""

Revision ID: 875766b17dda
Revises: 8016a49daba7
Create Date: 2020-11-04 12:46:33.954023

"""

# revision identifiers, used by Alembic.
revision = '875766b17dda'
down_revision = '8016a49daba7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('vendor_tags', sa.Column('details_url', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('vendor_tags', 'details_url')
