#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

from sqlalchemy import Column, Integer, Text

from lvfs import db


class Setting(db.Model):

    __tablename__ = "settings"

    setting_id = Column(Integer, primary_key=True)
    key = Column("config_key", Text)
    value = Column("config_value", Text)

    def __repr__(self) -> str:
        return "Setting object %s" % self.key
