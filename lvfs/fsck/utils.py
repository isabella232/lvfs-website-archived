#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+

from lvfs import db, tq

from lvfs.components.models import Component


def _fsck_update_descriptions(search: str, replace: str):

    for md in db.session.query(Component):
        if not md.release_description:
            continue
        if md.release_description.find(search) != -1:
            md.release_description = md.release_description.replace(search, replace)
    db.session.commit()


@tq.task(max_retries=3, default_retry_delay=5, task_time_limit=600)
def _async_fsck_update_descriptions(search: str, replace: str):
    _fsck_update_descriptions(search, replace)
