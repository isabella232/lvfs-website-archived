"""

Revision ID: fbe53b9b02d4
Revises: ac1903e703c1
Create Date: 2020-11-12 20:15:39.063398

"""

# revision identifiers, used by Alembic.
revision = 'fbe53b9b02d4'
down_revision = 'ac1903e703c1'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('event_log', sa.Column('container_id', sa.Text(), nullable=True))
    op.add_column('tests', sa.Column('container_id', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('tests', 'container_id')
    op.drop_column('event_log', 'container_id')
