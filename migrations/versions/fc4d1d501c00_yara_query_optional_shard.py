"""

Revision ID: fc4d1d501c00
Revises: d5d554c30ce4
Create Date: 2019-10-28 15:09:47.575231

"""

# revision identifiers, used by Alembic.
revision = 'fc4d1d501c00'
down_revision = 'd5d554c30ce4'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from lvfs import db
from lvfs.queries.models import YaraQueryResult

def upgrade():
    op.add_column('yara_query_result', sa.Column('component_id', sa.Integer(), nullable=False))
    op.alter_column('yara_query_result', 'component_shard_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)

    # migrate
    for result in db.session.query(YaraQueryResult):
        result.md = result.shard.md
    db.session.commit()

    op.create_foreign_key(None, 'yara_query_result', 'components', ['component_id'], ['component_id'])

def downgrade():
    op.drop_constraint(None, 'yara_query_result', type_='foreignkey')
    op.alter_column('yara_query_result', 'component_shard_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False)
    op.drop_column('yara_query_result', 'component_id')
