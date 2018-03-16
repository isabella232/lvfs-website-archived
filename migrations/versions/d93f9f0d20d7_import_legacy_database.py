"""

Revision ID: d93f9f0d20d7
Revises: None
Create Date: 2018-03-16 12:12:25.726037

"""

# revision identifiers, used by Alembic.
revision = 'd93f9f0d20d7'
down_revision = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    from app import db
    from app.models import Client, Firmware, Report

    # delete clients and reports without matching firmwares
    fws = {}
    for fw in db.session.query(Firmware).all():
        fws[fw.firmware_id] = fw
    for rprt in db.session.query(Report).all():
        if rprt.firmware_id not in fws:
            print('deleting report for missing firmware %s' % rprt.firmware_id)
            for attr in rprt.attributes:
                db.session.delete(attr)
            db.session.delete(rprt)
    db.session.commit()

    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_analytics_datestr'), 'analytics', ['datestr'], unique=False)
    op.drop_index('datestr', table_name='analytics')
    op.alter_column('clients', 'addr',
               existing_type=mysql.VARCHAR(length=40),
               nullable=False)
    op.create_index(op.f('ix_clients_firmware_id'), 'clients', ['firmware_id'], unique=False)
    op.create_index(op.f('ix_clients_timestamp'), 'clients', ['timestamp'], unique=False)
    op.drop_index('idx_firmware_id', table_name='clients')
    op.drop_index('timestamp_idx', table_name='clients')
    op.create_foreign_key(None, 'clients', 'firmware', ['firmware_id'], ['firmware_id'])
    op.alter_column('components', 'appstream_id',
               existing_type=mysql.TEXT(),
               nullable=False)
    op.alter_column('components', 'checksum_contents',
               existing_type=mysql.VARCHAR(length=40),
               nullable=False)
    op.alter_column('components', 'filename_contents',
               existing_type=mysql.TEXT(),
               nullable=False)
    op.alter_column('components', 'version',
               existing_type=mysql.VARCHAR(length=255),
               nullable=False)
    op.create_index(op.f('ix_components_component_id'), 'components', ['component_id'], unique=True)
    op.create_index(op.f('ix_components_firmware_id'), 'components', ['firmware_id'], unique=False)
    op.drop_index('idx_component_id', table_name='components')
    op.drop_index('idx_firmware_id', table_name='components')
    op.create_foreign_key(None, 'components', 'firmware', ['firmware_id'], ['firmware_id'])
    op.alter_column('conditions', 'key',
               existing_type=mysql.TEXT(),
               nullable=False)
    op.alter_column('conditions', 'value',
               existing_type=mysql.TEXT(),
               nullable=False)
    op.alter_column('event_log', 'addr',
               existing_type=mysql.VARCHAR(length=40),
               nullable=False)
    op.create_foreign_key(None, 'event_log', 'users', ['user_id'], ['user_id'])
    op.create_foreign_key(None, 'event_log', 'vendors', ['vendor_id'], ['vendor_id'])
    op.alter_column('firmware', 'addr',
               existing_type=mysql.VARCHAR(length=40),
               nullable=False)
    op.alter_column('firmware', 'checksum_signed',
               existing_type=mysql.VARCHAR(length=40),
               nullable=False)
    op.alter_column('firmware', 'checksum_upload',
               existing_type=mysql.VARCHAR(length=40),
               nullable=False)
    op.alter_column('firmware', 'filename',
               existing_type=mysql.VARCHAR(length=255),
               nullable=False)
    op.alter_column('firmware', 'target',
               existing_type=mysql.VARCHAR(length=255),
               nullable=False)
    op.create_index(op.f('ix_firmware_checksum_upload'), 'firmware', ['checksum_upload'], unique=False)
    op.create_index(op.f('ix_firmware_firmware_id'), 'firmware', ['firmware_id'], unique=True)
    op.drop_index('id', table_name='firmware')
    op.drop_index('idx_firmware_id', table_name='firmware')
    op.create_foreign_key(None, 'firmware', 'vendors', ['vendor_id'], ['vendor_id'])
    op.create_foreign_key(None, 'firmware', 'users', ['user_id'], ['user_id'])
    op.alter_column('firmware_events', 'target',
               existing_type=mysql.TEXT(),
               nullable=False)
    op.alter_column('guids', 'value',
               existing_type=mysql.TEXT(),
               nullable=False)
    op.create_foreign_key(None, 'issues', 'vendors', ['vendor_id'], ['vendor_id'])
    op.alter_column('keywords', 'value',
               existing_type=mysql.TEXT(),
               nullable=False)
    op.alter_column('report_attributes', 'key',
               existing_type=mysql.TEXT(),
               nullable=False)
    op.alter_column('reports', 'checksum',
               existing_type=mysql.VARCHAR(length=64),
               nullable=False)
    op.alter_column('reports', 'machine_id',
               existing_type=mysql.VARCHAR(length=64),
               nullable=False)
    op.create_index(op.f('ix_reports_firmware_id'), 'reports', ['firmware_id'], unique=False)
    op.drop_index('idx_firmware_id', table_name='reports')
    op.create_foreign_key(None, 'reports', 'firmware', ['firmware_id'], ['firmware_id'])
    op.alter_column('restrictions', 'value',
               existing_type=mysql.TEXT(),
               nullable=False)
    op.alter_column('search_events', 'value',
               existing_type=mysql.TEXT(),
               nullable=False)
    op.create_unique_constraint(None, 'users', ['user_id'])
    op.create_foreign_key(None, 'users', 'vendors', ['vendor_id'], ['vendor_id'])
    op.alter_column('vendors', 'description',
               existing_type=mysql.VARCHAR(length=255),
               nullable=True,
               existing_server_default=sa.text(u"''"))
    op.alter_column('vendors', 'display_name',
               existing_type=mysql.VARCHAR(length=128),
               nullable=True,
               existing_server_default=sa.text(u"''"))
    op.create_index(op.f('ix_vendors_group_id'), 'vendors', ['group_id'], unique=False)
    op.drop_index('id', table_name='vendors')
    op.create_unique_constraint(None, 'vendors', ['vendor_id'])
    # ### end Alembic commands ###

def downgrade():
    pass
