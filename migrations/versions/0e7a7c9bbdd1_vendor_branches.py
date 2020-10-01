"""

Revision ID: 0e7a7c9bbdd1
Revises: c1d0e4979f45
Create Date: 2020-09-30 10:40:33.762601

"""

# revision identifiers, used by Alembic.
revision = '0e7a7c9bbdd1'
down_revision = 'c1d0e4979f45'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('vendor_branches',
    sa.Column('branch_id', sa.Integer(), nullable=False),
    sa.Column('vendor_id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.Column('ctime', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
    sa.ForeignKeyConstraint(['vendor_id'], ['vendors.vendor_id'], ),
    sa.PrimaryKeyConstraint('branch_id')
    )
    op.create_index(op.f('ix_vendor_branches_vendor_id'), 'vendor_branches', ['vendor_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_vendor_branches_vendor_id'), table_name='vendor_branches')
    op.drop_table('vendor_branches')
