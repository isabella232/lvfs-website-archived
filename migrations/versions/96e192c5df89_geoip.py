"""

Revision ID: 96e192c5df89
Revises: 8f04bb816e2d
Create Date: 2020-10-24 11:11:12.586458

"""

# revision identifiers, used by Alembic.
revision = '96e192c5df89'
down_revision = '8f04bb816e2d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('geoips',
    sa.Column('geoip_id', sa.Integer(), nullable=False),
    sa.Column('addr_start', sa.BigInteger(), nullable=False),
    sa.Column('addr_end', sa.BigInteger(), nullable=False),
    sa.Column('country_code', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('geoip_id')
    )
    op.create_index(op.f('ix_geoips_addr_end'), 'geoips', ['addr_end'], unique=False)
    op.create_index(op.f('ix_geoips_addr_start'), 'geoips', ['addr_start'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_geoips_addr_start'), table_name='geoips')
    op.drop_index(op.f('ix_geoips_addr_end'), table_name='geoips')
    op.drop_table('geoips')
