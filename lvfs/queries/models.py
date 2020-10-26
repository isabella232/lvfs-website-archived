#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

import datetime
import functools
from typing import Optional, Dict

from flask import g

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from lvfs import db

from lvfs.users.models import User
from lvfs.components.models import Component


class YaraQueryResult(db.Model):

    __tablename__ = "yara_query_result"

    yara_query_result_id = Column(Integer, primary_key=True)
    yara_query_id = Column(
        Integer, ForeignKey("yara_query.yara_query_id"), nullable=False
    )
    component_shard_id = Column(
        Integer, ForeignKey("component_shards.component_shard_id"), nullable=True
    )
    component_id = Column(
        Integer, ForeignKey("components.component_id"), nullable=False
    )
    result = Column(Text, default=None)

    query = relationship("YaraQuery", foreign_keys=[yara_query_id])
    shard = relationship("ComponentShard", foreign_keys=[component_shard_id])
    md = relationship("Component", lazy="joined", foreign_keys=[component_id])

    def __repr__(self) -> str:
        return "<YaraQueryResult {}>".format(self.yara_query_result_id)


class YaraQuery(db.Model):

    __tablename__ = "yara_query"

    yara_query_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    value = Column(Text, default=None)
    error = Column(Text, default=None)
    found = Column(Integer, default=0)
    total = Column(Integer, default=0)
    ctime = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    started_ts = Column(DateTime, default=None)
    ended_ts = Column(DateTime, default=None)

    user = relationship("User", foreign_keys=[user_id])
    results = relationship(
        "YaraQueryResult", lazy="joined", cascade="all,delete,delete-orphan"
    )

    @property
    def color(self) -> str:
        if self.found and self.total:
            return "warning"
        if self.total:
            return "success"
        return "info"

    @property
    def title(self):
        for line in self.value.replace("{", "\n").split("\n"):
            if line.startswith("rule "):
                return line[5:]
        return None

    @property  # type: ignore
    @functools.lru_cache()
    def mds(self):
        mds: Dict[str, Component] = {}
        for result in self.results:
            key = "{} {}".format(result.md.fw.vendor.display_name, result.md.name)
            if key not in mds:
                mds[key] = result.md
        return mds

    def check_acl(self, action: str, user: Optional[User] = None) -> bool:

        # fall back
        if not user:
            user = g.user
        if not user:
            return False
        if user.check_acl("@admin"):
            return True

        # depends on the action requested
        if action == "@modify":
            if user.user_id == self.user_id:
                return True
            return False
        if action == "@delete":
            if user.user_id == self.user_id:
                return True
            return False
        if action == "@retry":
            if user.user_id == self.user_id:
                return True
            return False
        if action == "@show":
            if user.user_id == self.user_id:
                return True
            return False
        raise NotImplementedError(
            "unknown security check action: %s:%s" % (self, action)
        )

    def __repr__(self) -> str:
        return "<YaraQuery {}>".format(self.yara_query_id)
