"""

Revision ID: 7d2c4321b2ab
Revises: fbe53b9b02d4
Create Date: 2020-11-15 19:14:58.594798

"""

# revision identifiers, used by Alembic.
revision = '7d2c4321b2ab'
down_revision = 'fbe53b9b02d4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('licenses',
    sa.Column('license_id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('text', sa.Text(), nullable=True),
    sa.Column('is_content', sa.Boolean(), nullable=True),
    sa.Column('is_approved', sa.Boolean(), nullable=True),
    sa.Column('requires_source', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('license_id'),
    sa.UniqueConstraint('value')
    )
    op.add_column('components', sa.Column('metadata_license_id', sa.Integer(), nullable=True))
    op.add_column('components', sa.Column('project_license_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'components', 'licenses', ['metadata_license_id'], ['license_id'])
    op.create_foreign_key(None, 'components', 'licenses', ['project_license_id'], ['license_id'])


def downgrade():
    op.drop_constraint(None, 'components', type_='foreignkey')
    op.drop_constraint(None, 'components', type_='foreignkey')
    op.drop_column('components', 'project_license_id')
    op.drop_column('components', 'metadata_license_id')
    op.drop_table('licenses')
