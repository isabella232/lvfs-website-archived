"""

Revision ID: 234e715a953a
Revises: fc4d1d501c00
Create Date: 2019-10-29 13:55:09.790907

"""

# revision identifiers, used by Alembic.
revision = '234e715a953a'
down_revision = 'fc4d1d501c00'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from lvfs import db
from lvfs.components.models import ComponentShard, ComponentShardInfo

def upgrade():
    op.add_column('component_shards', sa.Column('guid', sa.String(length=36), nullable=True))
    op.add_column('component_shards', sa.Column('name', sa.Text(), nullable=True))
    op.alter_column('component_shards', 'component_shard_info_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)
    op.create_index(op.f('ix_component_shards_guid'), 'component_shards', ['guid'], unique=False)

    # migrate
    for shard in db.session.query(ComponentShard):
        shard.name = shard.info.name
        shard.guid = shard.info.guid
    db.session.commit()

def downgrade():
    op.drop_index(op.f('ix_component_shards_guid'), table_name='component_shards')
    op.alter_column('component_shards', 'component_shard_info_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False)
    op.drop_column('component_shards', 'name')
    op.drop_column('component_shards', 'guid')
