#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

from typing import List

from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from lvfs import db


class Category(db.Model):

    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True)
    value = Column(Text, nullable=False)  # 'X-System'
    name = Column(Text, default=None)  # 'System Update'
    icon = Column(Text, default=None)  # 'battery'
    unused_fallbacks = Column('fallbacks', Text, default=None)
    expect_device_checksum = Column(Boolean, default=False)
    fallback_id = Column(Integer, ForeignKey("categories.category_id"), nullable=True)

    fallback = relationship("Category", remote_side=[category_id])

    def matches(self, values: List[str]) -> bool:
        for value in values:
            if self.value == value:
                return True
            if self.fallback and self.fallback.value == value:
                return True
        return False

    def __repr__(self) -> str:
        return "Category object %s:%s" % (self.category_id, self.value)
