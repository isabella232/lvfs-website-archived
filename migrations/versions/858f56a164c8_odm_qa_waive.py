"""

Revision ID: 858f56a164c8
Revises: 1822ddbf2a73
Create Date: 2019-09-12 14:12:21.187892

"""

# revision identifiers, used by Alembic.
revision = '858f56a164c8'
down_revision = '1822ddbf2a73'

from lvfs import db
from lvfs.vendors.models import VendorAffiliation, VendorAffiliationAction

def upgrade():
    # add these by default
    for aff in db.session.query(VendorAffiliation):
        for action in ['@retry', '@waive']:
            aff.actions.append(VendorAffiliationAction(action=action, user_id=1))
    db.session.commit()

def downgrade():
    pass
