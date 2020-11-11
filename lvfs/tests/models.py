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

from sqlalchemy import Column, Integer, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from lvfs import db

from lvfs.users.models import User


class TestAttribute(db.Model):
    __tablename__ = "test_attributes"

    test_attribute_id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey("tests.test_id"), nullable=False, index=True)
    title = Column(Text, nullable=False)
    message = Column(Text, default=None)
    success = Column(Boolean, default=False)

    test = relationship("Test", back_populates="attributes")

    def __repr__(self) -> str:
        return "TestAttribute object %s=%s" % (self.title, self.message)


class Test(db.Model):

    __tablename__ = "tests"

    test_id = Column(Integer, primary_key=True)
    firmware_id = Column(
        Integer, ForeignKey("firmware.firmware_id"), nullable=False, index=True
    )
    plugin_id = Column(Text, default=None)
    waivable = Column(Boolean, default=False)
    scheduled_ts = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    started_ts = Column(DateTime, default=None)
    ended_ts = Column(DateTime, default=None)
    waived_ts = Column(DateTime, default=None)
    waived_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    max_age = Column(Integer, default=0)

    waived_user = relationship("User", foreign_keys=[waived_user_id])
    attributes = relationship(
        "TestAttribute",
        lazy="joined",
        back_populates="test",
        cascade="all,delete,delete-orphan",
    )

    fw = relationship("Firmware", back_populates="tests")

    def add_pass(self, title: str, message: Optional[str] = None) -> None:
        self.attributes.append(
            TestAttribute(title=title, message=message, success=True)
        )

    def add_fail(self, title: str, message: Optional[str] = None) -> None:
        self.attributes.append(
            TestAttribute(title=title, message=message, success=False)
        )

    def waive(self) -> None:
        self.waived_ts = datetime.datetime.utcnow()
        self.waived_user_id = g.user.user_id

    def retry(self) -> None:
        self.scheduled_ts = datetime.datetime.utcnow()
        self.started_ts = None
        self.ended_ts = None
        self.waived_ts = None
        for attr in self.attributes:
            db.session.delete(attr)

    def check_acl(self, action: str, user: Optional[User] = None) -> bool:

        # fall back
        if not user:
            user = g.user
        if not user:
            return False
        if user.check_acl("@admin"):
            return True

        # depends on the action requested
        if action == "@retry":
            if user.check_acl("@qa") and self.fw._is_permitted_action(action, user):
                return True
            if self.fw._is_owner(user):
                return True
            return False
        if action == "@waive":
            if user.check_acl("@qa") and self.fw._is_permitted_action(action, user):
                return True
            return False
        raise NotImplementedError(
            "unknown security check action: %s:%s" % (self, action)
        )

    @property
    def timestamp(self) -> DateTime:
        if self.ended_ts:
            return self.ended_ts
        if self.started_ts:
            return self.started_ts
        return self.scheduled_ts

    @property
    def is_pending(self) -> bool:
        if not self.started_ts:
            return True
        return False

    @property
    def is_waived(self) -> bool:
        if self.waived_ts:
            return True
        return False

    @property
    def is_running(self) -> bool:
        if self.started_ts and not self.ended_ts:
            return True
        return False

    @property
    def color(self) -> str:
        if self.success:
            return "success"
        if self.is_running:
            return "info"
        if self.is_pending:
            return "info"
        if self.is_waived:
            return "warning"
        return "danger"

    @property
    def success(self) -> bool:
        if not self.attributes:
            return True
        for attr in self.attributes:
            if not attr.success:
                return False
        return True

    def __repr__(self) -> str:
        return "Test object %s(%s)" % (self.plugin_id, self.success)
