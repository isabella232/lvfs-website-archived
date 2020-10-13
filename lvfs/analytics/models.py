#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

from enum import IntEnum

from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from lvfs import db


class Analytic(db.Model):

    __tablename__ = "analytics"

    datestr = Column(Integer, primary_key=True)
    cnt = Column(Integer, default=1)

    def __repr__(self):
        return "Analytic object %s" % self.datestr


class AnalyticVendor(db.Model):

    __tablename__ = "analytics_vendor"

    analytic_id = Column(Integer, primary_key=True)
    datestr = Column(Integer, default=0, index=True)
    vendor_id = Column(
        Integer, ForeignKey("vendors.vendor_id"), nullable=False, index=True
    )
    cnt = Column(Integer, default=0)

    vendor = relationship("Vendor", foreign_keys=[vendor_id])

    def __repr__(self):
        return "AnalyticVendor object %s:%s" % (self.datestr, self.vendor_id)


class AnalyticFirmware(db.Model):

    __tablename__ = "analytics_firmware"

    analytic_id = Column(Integer, primary_key=True)
    datestr = Column(Integer, default=0, index=True)
    firmware_id = Column(
        Integer, ForeignKey("firmware.firmware_id"), nullable=False, index=True
    )
    cnt = Column(Integer, default=0)

    firmware = relationship("Firmware", foreign_keys=[firmware_id])

    def __repr__(self):
        return "AnalyticFirmware object %s:%s" % (self.datestr, self.firmware_id)


class AnalyticUseragentKind(IntEnum):
    APP = 0
    FWUPD = 1
    LANG = 2
    DISTRO = 3


class AnalyticUseragent(db.Model):

    __tablename__ = "useragents"

    useragent_id = Column(Integer, primary_key=True)
    kind = Column(Integer, default=0, index=True)
    datestr = Column(Integer, default=0)
    value = Column(Text, default=None)
    cnt = Column(Integer, default=1)

    def __repr__(self):
        return "AnalyticUseragent object {}:{}".format(self.kind, self.datestr)
