"""

Revision ID: 8016a49daba7
Revises: dd9c6820993f
Create Date: 2020-11-04 09:32:00.459336

"""

# revision identifiers, used by Alembic.
revision = '8016a49daba7'
down_revision = 'dd9c6820993f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('categories', sa.Column('fallback_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'categories', 'categories', ['fallback_id'], ['category_id'])


def downgrade():
    op.drop_constraint(None, 'categories', type_='foreignkey')
    op.drop_column('categories', 'fallback_id')
