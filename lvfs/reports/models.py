#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods,protected-access

import datetime
from typing import Optional

from flask import g

from sqlalchemy import Column, Integer, Text, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from lvfs import db

from lvfs.users.models import User


class ReportAttribute(db.Model):
    __tablename__ = "report_attributes"

    report_attribute_id = Column(Integer, primary_key=True)
    report_id = Column(
        Integer, ForeignKey("reports.report_id"), nullable=False, index=True
    )
    key = Column(Text, nullable=False)
    value = Column(Text, default=None)

    report = relationship("Report", back_populates="attributes")

    def __lt__(self, other) -> bool:
        return self.key < other.key

    def __repr__(self):
        return "ReportAttribute object %s=%s" % (self.key, self.value)


class Report(db.Model):

    __tablename__ = "reports"

    report_id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    state = Column(Integer, default=0)
    machine_id = Column(String(64), nullable=False)
    firmware_id = Column(
        Integer, ForeignKey("firmware.firmware_id"), nullable=False, index=True
    )
    checksum = Column(String(64), nullable=False)  # remove?
    issue_id = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.user_id"), default=None)

    fw = relationship("Firmware", foreign_keys=[firmware_id])
    user = relationship("User", foreign_keys=[user_id])
    attributes = relationship(
        "ReportAttribute",
        back_populates="report",
        lazy="joined",
        cascade="all,delete,delete-orphan",
    )

    @property
    def color(self) -> str:
        if self.state == 1:
            return "info"
        if self.state == 2:
            return "success"
        if self.state == 3:
            if self.issue_id:
                return "info"
            return "danger"
        if self.state == 4:
            return "info"
        return "danger"

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
            # only admin
            return False
        if action == "@view":
            # QA user can modify any issues matching vendor_id
            if user.check_acl("@qa") and self.fw._is_vendor(user):
                return True
            return False
        raise NotImplementedError(
            "unknown security check action: %s:%s" % (self, action)
        )

    def __repr__(self):
        return "Report object %s" % self.report_id
