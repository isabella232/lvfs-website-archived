#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2019-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=singleton-comparison,too-many-nested-blocks

import datetime
from typing import List, Optional

from lvfs import db, ploader, tq

from lvfs.tests.models import Test
from lvfs.util import _event_log

def _test_priority_sort_func(test):
    plugin = ploader.get_by_id(test.plugin_id)
    if not plugin:
        return 0
    return plugin.priority

def _test_run_all(tests: Optional[List[Test]] = None) -> None:

    # make a list of the first few tests that need running
    if not tests:
        tests = db.session.query(Test)\
                          .filter(Test.started_ts == None)\
                          .order_by(Test.scheduled_ts)\
                          .limit(50).all()
        if not tests:
            return

    # mark all the tests as started
    for test in tests:
        print('Marking test {} started for firmware {}...'.format(test.plugin_id, test.fw.firmware_id))
        test.started_ts = datetime.datetime.utcnow()
    db.session.commit()

    # process each test
    for test in sorted(tests, key=_test_priority_sort_func):
        plugin = ploader.get_by_id(test.plugin_id)
        if not plugin:
            _event_log('No plugin %s' % test.plugin_id)
            test.ended_ts = datetime.datetime.utcnow()
            continue
        try:
            print('Running test {} for firmware {}'.format(test.plugin_id, test.fw.firmware_id))
            try:
                if not plugin.require_test_for_fw(test.fw):
                    continue
            except NotImplementedError as _:
                pass
            try:
                plugin.run_test_on_fw(test, test.fw)
            except NotImplementedError as _:
                pass
            for md in test.fw.mds:
                try:
                    if not plugin.require_test_for_md(md):
                        continue
                except NotImplementedError as _:
                    pass
                try:
                    plugin.run_test_on_md(test, md)
                except NotImplementedError as _:
                    pass
            test.ended_ts = datetime.datetime.utcnow()
            # don't leave a failed task running
            db.session.commit()
        except Exception as e: # pylint: disable=broad-except
            test.ended_ts = datetime.datetime.utcnow()
            test.add_fail('An exception occurred', str(e))

    # all done
    db.session.commit()

@tq.task(max_retries=3, default_retry_delay=600, task_time_limit=3600)
def _async_test_run_all():
    tests = db.session.query(Test)\
                      .filter(Test.started_ts == None)\
                      .all()
    if not tests:
        return
    _test_run_all(tests)

@tq.task(max_retries=3, default_retry_delay=5, task_time_limit=600)
def _async_test_run(test_id):
    tests = db.session.query(Test)\
                      .filter(Test.started_ts == None)\
                      .filter(Test.test_id == test_id)\
                      .all()
    if not tests:
        return
    _test_run_all(tests)

@tq.task(max_retries=3, default_retry_delay=60, task_time_limit=600)
def _async_test_run_for_firmware(firmware_id):
    tests = db.session.query(Test)\
                      .filter(Test.started_ts == None)\
                      .filter(Test.firmware_id == firmware_id)\
                      .order_by(Test.scheduled_ts)\
                      .all()
    if not tests:
        return
    _test_run_all(tests)
