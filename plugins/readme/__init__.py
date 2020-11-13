#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=no-self-use

import datetime
from typing import Optional, Dict

from cabarchive import CabFile
from pkgversion import vercmp

from lvfs.firmware.models import Firmware
from lvfs.pluginloader import (
    PluginBase,
    PluginError,
    PluginSettingText,
    PluginSettingBool,
)
from lvfs.util import _get_settings


def _get_fwupd_min_version(fw: Firmware) -> str:
    minver = "0.8.0"  # a guess, but everyone should have this
    for md in fw.mds:
        for req in md.requirements:
            if (
                req.kind == "id"
                and req.value == "org.freedesktop.fwupd"
                and req.compare == "ge"
            ):
                if vercmp(req.version, minver) > 0:
                    minver = req.version
    return minver


class Plugin(PluginBase):
    def __init__(self):
        PluginBase.__init__(self, "info-readme")
        self.name = "Readme"
        self.summary = "Add a README file to the archive"

    def settings(self):
        s = []
        s.append(PluginSettingBool("info_readme_enable", "Enabled", False))
        s.append(PluginSettingText("info_readme_filename", "Filename", "README.txt"))
        s.append(PluginSettingText("info_readme_template", "Template", "plugins/readme/template.txt"))
        return s

    def archive_finalize(self, cabarchive, fw):

        # read in the file
        try:
            fn = self.get_setting("info_readme_template", required=True)
            with open(fn, "rb") as f:
                template = f.read().decode("utf-8")
        except IOError as e:
            raise PluginError from e

        # do substititons
        settings = _get_settings()
        now = datetime.datetime.now().replace(microsecond=0)
        template = template.replace("$DATE$", now.isoformat())
        template = template.replace("$FWUPD_MIN_VERSION$", _get_fwupd_min_version(fw))
        template = template.replace("$CAB_FILENAME$", fw.filename)
        template = template.replace("$FIRMWARE_BASEURI$", settings["firmware_baseuri"])

        # add it to the archive
        filename = self.get_setting("info_readme_filename", required=True)
        cabarchive[filename] = CabFile(template.encode("utf-8"))
