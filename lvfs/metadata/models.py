#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

import datetime
from typing import Optional

from sqlalchemy import Column, Integer, Text, DateTime, Boolean
from sqlalchemy.orm import relationship

from lvfs import db

from lvfs.firmware.models import Firmware


class Remote(db.Model):

    __tablename__ = "remotes"

    remote_id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    is_public = Column(Boolean, default=False)
    is_dirty = Column(Boolean, default=False)
    build_cnt = Column(Integer, default=0)
    access_token = Column(Text, default=None)
    regenerate_ts = Column(DateTime, default=None)

    vendors = relationship("Vendor", back_populates="remote")
    fws = relationship("Firmware")

    def check_fw(self, fw: Firmware) -> bool:
        # remote is specified exactly
        if self.remote_id == fw.remote.remote_id:
            return True
        # odm uploaded to oem remote, but also include for odm
        if not self.is_public and fw.vendor_odm in self.vendors:
            return True
        return False

    @property
    def is_deleted(self) -> bool:
        return self.name == "deleted"

    @property
    def icon_name(self) -> Optional[str]:
        if self.name in ["private", "testing", "stable"]:
            return self.name
        if self.name == "deleted":
            return "trash"
        if self.name.startswith("embargo"):
            return "embargo"
        return None

    @property
    def description(self) -> Optional[str]:
        if self.name == "private":
            return "Only available to you"
        if self.name in ["testing", "stable"]:
            return "Available to the public"
        if self.name == "deleted":
            return "Deleted"
        if self.name.startswith("embargo"):
            return "Embargoed"
        return None

    @property
    def key(self) -> str:
        if self.name.startswith("embargo"):
            return "embargo"
        return self.name

    @property
    def is_signed(self) -> bool:
        return self.name != "deleted" and self.name != "private"

    @property
    def is_regenerating(self) -> bool:
        if not self.regenerate_ts:
            return False
        return datetime.datetime.utcnow() < self.regenerate_ts.replace(
            tzinfo=None
        ) + datetime.timedelta(hours=2)

    @property
    def build_str(self) -> str:
        if not self.build_cnt:
            return "00000"
        return "{:05d}".format(self.build_cnt)

    @property
    def filename(self) -> Optional[str]:
        if self.name == "private":
            return None
        if self.name == "stable":
            return "firmware-{}-stable.xml.gz".format(self.build_str)
        if self.name == "testing":
            return "firmware-{}-testing.xml.gz".format(self.build_str)
        return "firmware-{}-{}.xml.gz".format(self.build_str, self.access_token)

    @property
    def filename_newest(self) -> Optional[str]:
        if self.name == "private":
            return None
        if self.name == "stable":
            return "firmware.xml.gz"
        if self.name == "testing":
            return "firmware-testing.xml.gz"
        return "firmware-%s.xml.gz" % self.access_token

    @property
    def scheduled_signing(self) -> DateTime:
        now = datetime.datetime.now()
        if not self.is_public:
            return now
        secs = (((4 - (now.hour % 4)) * 60) + (60 - now.minute)) * 60 + (
            60 - now.second
        )
        return datetime.datetime.now() + datetime.timedelta(seconds=secs)

    def __repr__(self) -> str:
        return "Remote object %s [%s]" % (self.remote_id, self.name)
