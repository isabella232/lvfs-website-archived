#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

import datetime

from sqlalchemy import Column, Integer, Text, DateTime

from lvfs import db


class Agreement(db.Model):

    __tablename__ = "agreements"

    agreement_id = Column(Integer, primary_key=True)
    created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    version = Column(Integer, nullable=False)
    text = Column(Text, default=None)
