"""

Revision ID: dd9c6820993f
Revises: 96e192c5df89
Create Date: 2020-11-03 13:06:23.824906

"""

# revision identifiers, used by Alembic.
revision = 'dd9c6820993f'
down_revision = '96e192c5df89'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('vendor_tags',
    sa.Column('vendor_tag_id', sa.Integer(), nullable=False),
    sa.Column('vendor_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('example', sa.Text(), nullable=True),
    sa.Column('enforce', sa.Boolean(), nullable=True),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('ctime', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.category_id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
    sa.ForeignKeyConstraint(['vendor_id'], ['vendors.vendor_id'], ),
    sa.PrimaryKeyConstraint('vendor_tag_id')
    )
    op.create_index(op.f('ix_vendor_tags_vendor_id'), 'vendor_tags', ['vendor_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_vendor_tags_vendor_id'), table_name='vendor_tags')
    op.drop_table('vendor_tags')
