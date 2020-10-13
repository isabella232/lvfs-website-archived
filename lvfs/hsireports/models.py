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

from flask import g

from sqlalchemy import Column, Integer, Text, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from lvfs import db

from lvfs.users.models import User


class HsiReportAttr(db.Model):
    __tablename__ = "hsi_report_attrs"

    report_attr_id = Column(Integer, primary_key=True)
    hsi_report_id = Column(
        Integer, ForeignKey("hsi_reports.hsi_report_id"), nullable=False, index=True
    )
    appstream_id = Column(Text, nullable=False)
    hsi_result = Column(Text, default=None)
    is_success = Column(Boolean, default=False)
    is_runtime = Column(Boolean, default=False)
    is_obsoleted = Column(Boolean, default=False)

    report = relationship("HsiReport", back_populates="attrs")

    def __repr__(self):
        return "HsiReportAttr object %s=%s" % (self.key, self.value)


class HsiReport(db.Model):

    __tablename__ = "hsi_reports"

    hsi_report_id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    payload = Column(Text, nullable=False)
    signature = Column(Text, default=None)
    machine_id = Column(String(64), nullable=False)
    distro = Column(Text, default=None)
    kernel_cmdline = Column(Text, default=None)
    kernel_version = Column(Text, default=None)
    host_product = Column(Text, default=None, index=True)
    host_vendor = Column(Text, default=None, index=True)
    host_family = Column(Text, default=None, index=True)
    host_sku = Column(Text, default=None, index=True)
    host_security_id = Column(Text, nullable=False)
    host_security_version = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), default=None)

    user = relationship("User", foreign_keys=[user_id])
    attrs = relationship(
        "HsiReportAttr", back_populates="report", cascade="all,delete,delete-orphan"
    )

    @property
    def host_sku_sane(self) -> Optional[str]:
        if self.host_sku == "To be filled by O.E.M.":
            return None
        if self.host_sku == "Default string":
            return None
        return self.host_sku

    def check_acl(self, action: str, user: Optional[User] = None) -> bool:

        # fall back
        if not user:
            user = g.user
        if not user:
            return False
        if user.check_acl("@admin"):
            return True

        # depends on the action requested
        if action == "@delete":
            return False
        if action == "@view":
            return True
        raise NotImplementedError(
            "unknown security check action: %s:%s" % (self, action)
        )

    def __repr__(self):
        return "HsiReport object {}".format(self.hsi_report_id)
