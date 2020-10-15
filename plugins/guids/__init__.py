#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2019-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=no-self-use

import struct

from lvfs import db

from lvfs.pluginloader import PluginBase, PluginError, PluginSettingBool
from lvfs.components.models import Component
from lvfs.firmware.models import Firmware
from lvfs.metadata.models import Remote
from lvfs.tests.models import Test


def _test_dropped_guid(test, md: Component) -> None:

    new_guids = [guid.value for guid in md.guids]
    for md_tmp in (
        db.session.query(Component)
        .filter(Component.appstream_id == md.appstream_id)
        .join(Firmware)
        .filter(Firmware.firmware_id < md.fw.firmware_id)
        .join(Remote)
        .filter(Remote.name != "deleted")
    ):
        for old_guid in [guid.value for guid in md_tmp.guids]:
            if old_guid in new_guids:
                continue

            test.add_fail(
                "GUID dropped",
                "Firmware drops GUID {} previously supported "
                "in firmware {}".format(old_guid, str(md_tmp.fw.firmware_id)),
            )


class Plugin(PluginBase):
    def __init__(self):
        PluginBase.__init__(self)
        self.name = "GUIDs"
        self.summary = "Check firmware GUIDs are correct"

    def settings(self):
        s = []
        s.append(PluginSettingBool("guids_enable", "Enabled", True))
        return s

    def ensure_test_for_fw(self, fw):

        # add if not already exists
        test = fw.find_test_by_plugin_id(self.id)
        if not test:
            test = Test(plugin_id=self.id, waivable=True)
            fw.tests.append(test)

    def run_test_on_md(self, test, md):

        # check if the file dropped a GUID previously supported
        _test_dropped_guid(test, md)
