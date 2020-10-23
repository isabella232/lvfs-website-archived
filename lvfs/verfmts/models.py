#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

from typing import Optional

from sqlalchemy import Column, Integer, Text

from lvfs import db


class Verfmt(db.Model):

    __tablename__ = "verfmts"

    verfmt_id = Column(Integer, primary_key=True)
    value = Column(Text, nullable=False)  # 'dell-bios'
    name = Column(Text, default=None)  # 'Dell Style'
    example = Column(Text, default=None)  # '12.34.56.78'
    fwupd_version = Column(Text, default=None)  # '1.3.3'
    fallbacks = Column(Text, default=None)  # 'quad,intelme'

    @property
    def sections(self) -> int:
        if not self.example:
            return 0
        return len(self.example.split("."))

    def _uint32_to_str(self, v: int) -> Optional[str]:
        if self.value == "plain":
            return str(v)
        if self.value == "quad":
            return "%i.%i.%i.%i" % (
                (v & 0xFF000000) >> 24,
                (v & 0x00FF0000) >> 16,
                (v & 0x0000FF00) >> 8,
                v & 0x000000FF,
            )
        if self.value == "triplet":
            return "%i.%i.%i" % (
                (v & 0xFF000000) >> 24,
                (v & 0x00FF0000) >> 16,
                v & 0x0000FFFF,
            )
        if self.value == "pair":
            return "%i.%i" % ((v & 0xFFFF0000) >> 16, v & 0x0000FFFF)
        if self.value == "intel-me":
            return "%i.%i.%i.%i" % (
                ((v & 0xE0000000) >> 29) + 0x0B,
                (v & 0x1F000000) >> 24,
                (v & 0x00FF0000) >> 16,
                v & 0x0000FFFF,
            )
        if self.value == "intel-me2":
            return "%i.%i.%i.%i" % (
                (v & 0xF0000000) >> 28,
                (v & 0x0F000000) >> 24,
                (v & 0x00FF0000) >> 16,
                v & 0x0000FFFF,
            )
        if self.value == "surface-legacy":
            return "%i.%i.%i" % ((v >> 22) & 0x3FF, (v >> 10) & 0xFFF, v & 0x3FF)
        if self.value == "surface":
            return "%i.%i.%i" % ((v >> 24) & 0xFF, (v >> 8) & 0xFFFF, v & 0xFF)
        if self.value == "bcd":
            return "%i.%i" % ((v & 0xF0) >> 4, v & 0x0F)
        if self.value == "dell-bios":
            return "%i.%i.%i" % (
                (v & 0x00FF0000) >> 16,
                (v & 0x0000FF00) >> 8,
                v & 0x000000FF,
            )
        if self.value == "number":
            return "%i" % v
        if self.value == "hex":
            return "%#08x" % v
        return None

    def version_display(self, version: str) -> Optional[str]:
        if version.isdigit():
            return self._uint32_to_str(int(version))
        return version

    def __repr__(self) -> str:
        return "Verfmt object %s:%s" % (self.verfmt_id, self.value)
