#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

import fnmatch
import re
from typing import Optional, Dict

from flask import g

from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from pkgversion import vercmp

from lvfs import db

from lvfs.users.models import User


class IssueCondition(db.Model):

    __tablename__ = "conditions"

    condition_id = Column(Integer, primary_key=True)
    issue_id = Column(
        Integer, ForeignKey("issues.issue_id"), nullable=False, index=True
    )
    key = Column(Text, nullable=False)
    value = Column(Text, nullable=False)
    compare = Column(Text, default="eq", nullable=False)

    issue = relationship("Issue", back_populates="conditions")

    def matches(self, value: str) -> bool:
        if self.compare == "eq":
            return value == self.value
        if self.compare == "lt":
            return vercmp(value, self.value) < 0
        if self.compare == "le":
            return vercmp(value, self.value) <= 0
        if self.compare == "gt":
            return vercmp(value, self.value) > 0
        if self.compare == "ge":
            return vercmp(value, self.value) >= 0
        if self.compare == "glob":
            return fnmatch.fnmatch(value, self.value)
        if self.compare == "regex":
            return bool(re.search(self.value, value))
        return False

    @property
    def relative_cost(self) -> int:
        if self.compare == "eq":
            return 0
        if self.compare in ["lt", "le", "gt", "ge"]:
            return 1
        if self.compare == "glob":
            return 5
        if self.compare == "regex":
            return 10
        return -1

    def __repr__(self):
        return "IssueCondition object %s %s %s" % (self.key, self.compare, self.value)


class Issue(db.Model):

    __tablename__ = "issues"

    issue_id = Column(Integer, primary_key=True)
    priority = Column(Integer, default=0)
    enabled = Column(Boolean, default=False)
    vendor_id = Column(Integer, ForeignKey("vendors.vendor_id"), nullable=False)
    url = Column(Text, default="")
    name = Column(Text, default=None)
    description = Column(Text, default="")
    conditions = relationship(
        "IssueCondition", back_populates="issue", cascade="all,delete,delete-orphan"
    )

    vendor = relationship("Vendor", foreign_keys=[vendor_id])

    def matches(self, data: Dict) -> bool:
        """ if all conditions are satisfied from data """
        for condition in sorted(self.conditions, key=lambda x: x.relative_cost):
            if not condition.key in data:
                return False
            if not condition.matches(data[condition.key]):
                return False
        return True

    def check_acl(self, action: str, user: Optional[User] = None) -> bool:

        # fall back
        if not user:
            user = g.user
        if not user:
            return False
        if user.check_acl("@admin"):
            return True

        # depends on the action requested
        if action == "@create":
            return user.check_acl("@qa")
        if action == "@modify":
            if user.check_acl("@qa") and user.vendor_id == self.vendor_id:
                return True
            return False
        if action == "@view":
            if user.check_acl("@qa") and user.vendor_id == self.vendor_id:
                return True
            # any issues owned by admin can be viewed by a QA user
            if user.check_acl("@qa") and self.vendor_id == 1:
                return True
            return False
        raise NotImplementedError(
            "unknown security check action: %s:%s" % (self, action)
        )

    def __repr__(self):
        return "Issue object %s" % self.url
