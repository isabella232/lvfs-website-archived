#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from lvfs import db


class Protocol(db.Model):

    __tablename__ = "protocol"

    protocol_id = Column(Integer, primary_key=True)
    value = Column(Text, nullable=False)
    name = Column(Text, default=None)
    is_signed = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    can_verify = Column(Boolean, default=False)
    has_header = Column(Boolean, default=False)
    verfmt_id = Column(Integer, ForeignKey("verfmts.verfmt_id"))

    verfmt = relationship("Verfmt", foreign_keys=[verfmt_id])

    def __repr__(self):
        return "Protocol object %s:%s" % (self.protocol_id, self.value)
