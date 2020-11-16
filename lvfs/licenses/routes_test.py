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
    def test_licenses(self):

        self.login()
        self.upload()
        rv = self.app.get("/lvfs/licenses/")
        assert "MPL" not in rv.data.decode("utf-8"), rv.data

        # create
        rv = self.app.post(
            "/lvfs/licenses/create",
            data=dict(
                value="MPL",
            ),
            follow_redirects=True,
        )
        assert b"Added license" in rv.data, rv.data.decode()
        rv = self.app.get("/lvfs/licenses/")
        assert "MPL" in rv.data.decode("utf-8"), rv.data.decode()
        rv = self.app.post(
            "/lvfs/licenses/create",
            data=dict(
                value="MPL",
            ),
            follow_redirects=True,
        )
        assert b"already exists" in rv.data, rv.data.decode()

        # modify
        rv = self.app.post(
            "/lvfs/licenses/4/modify",
            data=dict(
                name="ACME",
            ),
            follow_redirects=True,
        )
        assert b"Modified license" in rv.data, rv.data.decode()
        rv = self.app.get("/lvfs/licenses/")
        assert "ACME" in rv.data.decode("utf-8"), rv.data.decode()

        # show
        rv = self.app.get("/lvfs/licenses/4", follow_redirects=True)
        assert b"ACME" in rv.data, rv.data.decode()

        # delete
        rv = self.app.post("/lvfs/licenses/4/delete", follow_redirects=True)
        assert b"Deleted license" in rv.data, rv.data.decode()
        rv = self.app.get("/lvfs/licenses/")
        assert "MPL" not in rv.data.decode("utf-8"), rv.data.decode()


if __name__ == "__main__":
    unittest.main()
