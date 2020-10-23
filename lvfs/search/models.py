#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

import datetime

from sqlalchemy import Column, Integer, Text, String, DateTime

from lvfs import db


class SearchEvent(db.Model):

    __tablename__ = "search_events"

    search_event_id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    addr = Column(String(40), nullable=False)
    value = Column(Text, nullable=False)
    count = Column(Integer, default=0)
    method = Column(Text, default=None)

    def __repr__(self) -> str:
        return "SearchEvent object %s" % self.search_event_id
