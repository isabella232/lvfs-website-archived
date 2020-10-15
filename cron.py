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
import hashlib

from flask import g

from lvfs import app, db, ploader

from lvfs.components.models import Component
from lvfs.firmware.models import Firmware
from lvfs.users.models import User
from lvfs.util import _get_sanitized_basename

def _repair_fn():
    for firmware_id, in db.session.query(Firmware.firmware_id)\
                                  .order_by(Firmware.firmware_id.asc()):
        fw = db.session.query(Firmware)\
                       .filter(Firmware.firmware_id == firmware_id)\
                       .one()
        filename = _get_sanitized_basename(fw.filename)
        if filename != fw.filename:

            print('moving {} to {}'.format(fw.filename, filename))
            fn_old = fw.absolute_path
            fn_new = os.path.join(os.path.dirname(fn_old), filename)
            try:
                os.rename(fn_old, fn_new)
                fw.filename = filename
                fw.mark_dirty()
            except FileNotFoundError as _:
                pass

    # all done
    db.session.commit()

def _fsck():
    for firmware_id, in db.session.query(Firmware.firmware_id)\
                                  .order_by(Firmware.firmware_id.asc()):
        fw = db.session.query(Firmware)\
                       .filter(Firmware.firmware_id == firmware_id)\
                       .one()
        fn = fw.absolute_path
        if not os.path.isfile(fn):
            print('firmware {} is missing, expected {}'.format(fw.firmware_id, fn))

def _repair_tests():

    # fix all the PFAT tests
    for component_id, in db.session.query(Component.component_id)\
                                   .filter(Component.verfmt_id == None)\
                                   .filter(Component.protocol_id == 17)\
                                   .order_by(Component.component_id.asc()):
        md = db.session.query(Component)\
                       .filter(Component.component_id == component_id)\
                       .one()
        if md.blob[8:16] == b'_AMIPFAT':
            for test in md.fw.tests:
                if test.plugin_id in ['uefi-extract',
                                      'microcode',
                                      'shard-claim',
                                      'microcode-mcedb',
                                      'intelme']:
                    test.retry()
            print('Retrying tests for component {} ({})'.format(md.component_id, md.name_with_vendor))

    # all done
    db.session.commit()

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

def _repair_csum():

    # fix all the checksums and file sizes
    for firmware_id, in db.session.query(Firmware.firmware_id)\
                                  .order_by(Firmware.firmware_id.asc()):
        fw = db.session.query(Firmware)\
                       .filter(Firmware.firmware_id == firmware_id)\
                       .one()
        try:
            print('checking {}…'.format(fw.filename_absolute))
            fn = fw.absolute_path
            with open(fn, 'rb') as f:
                buf = f.read()
                checksum_signed_sha1 = hashlib.sha1(buf).hexdigest()
                if checksum_signed_sha1 != fw.checksum_signed_sha1:
                    print('repairing checksum from {} to {}'.format(fw.checksum_signed_sha1,
                                                                    checksum_signed_sha1))
                    fw.checksum_signed_sha1 = checksum_signed_sha1
                    fw.mark_dirty()
                checksum_signed_sha256 = hashlib.sha256(buf).hexdigest()
                if checksum_signed_sha256 != fw.checksum_signed_sha256:
                    print('repairing checksum from {} to {}'.format(fw.checksum_signed_sha256,
                                                                    checksum_signed_sha256))
                    fw.checksum_signed_sha256 = checksum_signed_sha256
                    fw.mark_dirty()
            sz = os.path.getsize(fn)
            for md in fw.mds:
                if sz != md.release_download_size:
                    print('repairing size from {} to {}'.format(md.release_download_size, sz))
                    md.release_download_size = sz
                    md.fw.mark_dirty()
        except FileNotFoundError as _:
            print('skipping {}'.format(fw.filename_absolute))

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
    if 'repair-fn' in sys.argv:
        _repair_fn()
    if 'repair-csum' in sys.argv:
        _repair_csum()
    if 'repair-verfmt' in sys.argv:
        _repair_verfmt()
    if 'repair-tests' in sys.argv:
        _repair_tests()
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
