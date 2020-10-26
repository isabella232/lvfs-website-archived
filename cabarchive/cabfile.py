#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018-2019 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+

from typing import Optional


class CabFile:
    def __init__(self, buf: Optional[bytes] = None, filename: Optional[str] = None):
        """ Set defaults """
        self.filename = filename
        self.buf = buf

    def __len__(self) -> int:
        if not self.buf:
            return 0
        return len(self.buf)

    def __repr__(self) -> str:
        if not self.buf:
            return "CabFile({})".format(self.filename)
        return "CabFile({}:{:x})".format(self.filename, len(self.buf))
