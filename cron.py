#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=singleton-comparison

import sys

from flask import g

from lvfs import app, db, ploader

from lvfs.firmware.models import Firmware
from lvfs.users.models import User

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
