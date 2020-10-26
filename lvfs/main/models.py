#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

import datetime

from sqlalchemy import Column, Integer, Text, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from lvfs import db


class Event(db.Model):

    __tablename__ = "event_log"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    vendor_id = Column(
        Integer, ForeignKey("vendors.vendor_id"), nullable=False, index=True
    )
    address = Column("addr", String(40), nullable=False)
    message = Column(Text, default=None)
    is_important = Column(Boolean, default=False)
    request = Column(Text, default=None)

    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return "Event object %s" % self.message


class Client(db.Model):

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    timestamp = Column(
        DateTime, nullable=False, default=datetime.datetime.utcnow, index=True
    )
    datestr = Column(Integer, default=0, index=True)
    firmware_id = Column(
        Integer, ForeignKey("firmware.firmware_id"), nullable=False, index=True
    )
    user_agent = Column(Text, default=None)

    fw = relationship("Firmware", foreign_keys=[firmware_id])

    def __repr__(self) -> str:
        return "Client object %s" % self.id


class ClientMetric(db.Model):

    __tablename__ = "metrics"

    setting_id = Column(Integer, primary_key=True)
    key = Column(Text, nullable=False)
    value = Column(Integer, default=0)

    def __repr__(self) -> str:
        return "ClientMetric object {}={}".format(self.key, self.value)
