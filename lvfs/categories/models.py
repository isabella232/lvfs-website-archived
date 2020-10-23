#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

from typing import List

from sqlalchemy import Column, Integer, Text, Boolean

from lvfs import db


class Category(db.Model):

    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True)
    value = Column(Text, nullable=False)  # 'X-System'
    name = Column(Text, default=None)  # 'System Update'
    fallbacks = Column(Text, default=None)
    expect_device_checksum = Column(Boolean, default=False)

    def matches(self, values: List[str]) -> bool:
        for value in values:
            if self.value == value:
                return True
        if self.fallbacks:
            for value in values:
                if value in self.fallbacks.split(","):
                    return True
        return False

    def __repr__(self) -> str:
        return "Category object %s:%s" % (self.category_id, self.value)
