#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

from sqlalchemy import Column, Integer, Text, Boolean

from lvfs import db


class License(db.Model):

    __tablename__ = "licenses"

    license_id = Column(Integer, primary_key=True)
    value = Column(Text, nullable=False, unique=True)  # 'CC0-1.0'
    name = Column(Text, default=None)  # 'Creative Commons Zero'
    text = Column(Text, default=None)  # 'THE LICENSE TEXT'
    is_content = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    requires_source = Column(Boolean, default=False)

    def __repr__(self) -> str:
        return "License object %s:%s" % (self.license_id, self.value)
