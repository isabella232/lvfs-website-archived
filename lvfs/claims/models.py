#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

from typing import List

from sqlalchemy import Column, Integer, Text

from lvfs import db


class Claim(db.Model):

    __tablename__ = "claims"

    claim_id = Column(Integer, primary_key=True)
    kind = Column(Text, nullable=False, index=True)
    icon = Column(Text)  # e.g. 'success'
    summary = Column(Text)
    description = Column(Text, default=None)
    url = Column(Text)

    def __lt__(self, other) -> bool:
        if self.icon != other.icon:
            return self.icon < other.icon
        return self.kind < other.kind

    def __eq__(self, other) -> bool:
        return self.kind == other.kind

    @property
    def icon_css(self) -> List[str]:
        if self.icon in ["danger", "warning"]:
            return ["fas", "fa-times-circle", "text-" + self.icon]
        if self.icon == "info":
            return ["fas", "fa-info-circle", "text-" + self.icon]
        if self.icon == "success":
            return ["fas", "fa-check-circle", "text-" + self.icon]
        if self.icon == "waiting":
            return ["far", "fa-clock", "text-info"]
        return ["far", "fa-{}".format(self.icon)]

    def __repr__(self) -> str:
        return "Claim object {}:{}->{}".format(self.claim_id, self.kind, self.icon)
