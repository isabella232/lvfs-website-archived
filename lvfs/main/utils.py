#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2019-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=singleton-comparison

from typing import Dict

from lvfs import db, tq

from lvfs.components.models import ComponentShardInfo, ComponentShard, Component
from lvfs.dbutils import _execute_count_star
from lvfs.firmware.models import Firmware
from lvfs.metadata.models import Remote
from lvfs.protocols.models import Protocol
from lvfs.reports.models import Report
from lvfs.tests.models import Test
from lvfs.users.models import User
from lvfs.vendors.models import Vendor

from .models import Client, ClientMetric

def _regenerate_metrics():
    values: Dict[str, int] = {}
    values['ClientCnt'] = _execute_count_star(\
                                db.session.query(Client))
    values['FirmwareCnt'] = _execute_count_star(\
                                db.session.query(Firmware))
    values['FirmwareStableCnt'] = _execute_count_star(\
                                db.session.query(Firmware)\
                                          .join(Remote)\
                                          .filter(Remote.name == 'stable'))
    values['FirmwareTestingCnt'] = _execute_count_star(\
                                db.session.query(Firmware)\
                                          .join(Remote)\
                                          .filter(Remote.name == 'testing'))
    values['FirmwarePrivateCnt'] = _execute_count_star(\
                                db.session.query(Firmware)\
                                          .join(Remote)\
                                          .filter(Remote.is_public == False))
    values['TestCnt'] = _execute_count_star(\
                                db.session.query(Test))
    values['ReportCnt'] = _execute_count_star(\
                                db.session.query(Report))
    values['ProtocolCnt'] = _execute_count_star(\
                                db.session.query(Protocol))
    values['ComponentShardInfoCnt'] = _execute_count_star(\
                                db.session.query(ComponentShardInfo))
    values['ComponentShardCnt'] = _execute_count_star(\
                                db.session.query(ComponentShard))
    values['ComponentCnt'] = _execute_count_star(\
                                db.session.query(Component))
    values['VendorCnt'] = _execute_count_star(\
                                db.session.query(Vendor)\
                                          .filter(Vendor.visible)\
                                          .filter(Vendor.username_glob != None))
    values['UserCnt'] = _execute_count_star(\
                                db.session.query(User)\
                                         .filter(User.auth_type != 'disabled'))

    #  save to database
    for key in values:
        metric = db.session.query(ClientMetric).filter(ClientMetric.key == key).first()
        if not metric:
            metric = ClientMetric(key=key)
            db.session.add(metric)
        metric.value = values[key]
        print('{}={}'.format(metric.key, metric.value))
    db.session.commit()

@tq.task(max_retries=3, default_retry_delay=60, task_time_limit=600)
def _async_regenerate_metrics():
    _regenerate_metrics()
