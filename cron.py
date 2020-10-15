#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=singleton-comparison

import os
import sys

from flask import g

from lvfs import app, db, ploader

from lvfs.components.models import Component
from lvfs.firmware.models import Firmware
from lvfs.users.models import User

def _fsck():
    for firmware_id, in db.session.query(Firmware.firmware_id)\
                                  .order_by(Firmware.firmware_id.asc()):
        fw = db.session.query(Firmware)\
                       .filter(Firmware.firmware_id == firmware_id)\
                       .one()
        fn = fw.absolute_path
        if not os.path.isfile(fn):
            print('firmware {} is missing, expected {}'.format(fw.firmware_id, fn))

def _repair_verfmt():

    # fix all the checksums and file sizes
    for component_id, in db.session.query(Component.component_id)\
                                   .filter(Component.verfmt_id == None)\
                                   .order_by(Component.component_id.asc()):
        md = db.session.query(Component)\
                       .filter(Component.component_id == component_id)\
                       .one()
        if md.protocol and md.protocol.verfmt:
            md.verfmt = md.protocol.verfmt
            print('repairing Component {} verfmt to {} using protocol {}'\
                  .format(md.component_id, md.verfmt.value, md.protocol.value))
            continue
        if md.fw.vendor.verfmt and md.protocol and md.protocol.value == 'org.uefi.capsule':
            md.verfmt = md.fw.vendor.verfmt
            print('repairing Component {} verfmt to {} using vendor'\
                  .format(md.component_id, md.verfmt.value))
            continue

    # all done
    db.session.commit()

def _ensure_tests():

    # ensure the test has been added for the firmware type
    for firmware_id, in db.session.query(Firmware.firmware_id)\
                                  .order_by(Firmware.timestamp):
        fw = db.session.query(Firmware)\
                       .filter(Firmware.firmware_id == firmware_id)\
                       .one()
        if not fw.is_deleted:
            ploader.ensure_test_for_fw(fw)
            db.session.commit()

def _main_with_app_context():
    if 'repair-verfmt' in sys.argv:
        _repair_verfmt()
    if 'fsck' in sys.argv:
        _fsck()
    if 'ensure' in sys.argv:
        _ensure_tests()

if __name__ == '__main__':

    if len(sys.argv) < 2:
        sys.exit(1)
    try:
        with app.test_request_context():
            app.config['SERVER_NAME'] = app.config['HOST_NAME']
            g.user = db.session.query(User).filter(User.username == 'anon@fwupd.org').first()
            _main_with_app_context()
    except NotImplementedError as e:
        print(str(e))
        sys.exit(1)

    # success
    sys.exit(0)
