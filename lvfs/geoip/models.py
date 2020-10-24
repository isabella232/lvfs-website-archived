#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

from sqlalchemy import Column, Integer, Text, BigInteger

from lvfs import db


class Geoip(db.Model):

    __tablename__ = "geoips"

    geoip_id = Column(Integer, primary_key=True)
    addr_start = Column(BigInteger, nullable=False, index=True)
    addr_end = Column(BigInteger, nullable=False, index=True)
    country_code = Column(Text, default=None)
