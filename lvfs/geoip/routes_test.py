#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=wrong-import-position,singleton-comparison

import os
import sys
import unittest

sys.path.append(os.path.realpath("."))

from lvfs.testcase import LvfsTestCase


class LocalTestCase(LvfsTestCase):
    def test_eventlog(self) -> None:

        self.login()
        rv = self.app.post(
            "/lvfs/geoip/import/data",
            data=dict(addr_start=0x1020301, addr_end=0x1020309, country_code="SY",),
            follow_redirects=True,
        )
        assert b"Added GeoIP data" in rv.data, rv.data.decode()

        rv = self.app.post(
            "/lvfs/geoip/check", data=dict(ip_addr="1.2.3.4",), follow_redirects=True
        )
        assert b"Country code: SY" in rv.data, rv.data.decode()

        rv = self.app.post(
            "/lvfs/geoip/check", data=dict(ip_addr="1.2.3",), follow_redirects=True
        )
        assert b"Cannot parse IP address" in rv.data, rv.data.decode()

        rv = self.app.post(
            "/lvfs/geoip/check", data=dict(ip_addr="dave",), follow_redirects=True
        )
        assert b"Cannot parse IP address" in rv.data, rv.data.decode()

        rv = self.app.post(
            "/lvfs/geoip/check", data=dict(ip_addr="2.3.4.5",), follow_redirects=True
        )
        assert b"Cannot find IP range" in rv.data, rv.data.decode()


if __name__ == "__main__":
    unittest.main()
