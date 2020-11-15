#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=no-self-use

import os
from typing import Dict

from cabarchive import CabFile
from lvfs.pluginloader import (
    PluginBase,
    PluginError,
    PluginSettingText,
    PluginSettingBool,
)


class Plugin(PluginBase):
    def __init__(self):
        PluginBase.__init__(self, "license")
        self.name = "License"
        self.summary = "Add a LICENSE.txt file to the archive"

    def settings(self):
        s = []
        s.append(PluginSettingBool("license_enable", "Enabled", False))
        s.append(PluginSettingText("license_filename", "Filename", "LICENSE.txt"))
        return s

    def archive_finalize(self, cabarchive, fw):

        # add all the known licences to the archive
        contents: Dict[str, str] = {}
        for md in fw.mds:
            if (
                md.project_license
                and md.project_license.is_approved
                and md.project_license.text
            ):
                contents[md.project_license.value] = md.project_license.text

        # add to the archive if required
        if not contents:
            return
        filename = self.get_setting("license_filename", required=True)
        cabarchive[filename] = CabFile("\n\n\n".join(contents.values()).encode("utf-8"))
