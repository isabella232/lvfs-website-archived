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
    def test_cron_fsck(self):

        # verify all fsck is in good shape
        self.login()
        rv = self.app.get("/lvfs/fsck/update_descriptions")
        assert b"Updating update descriptions" not in rv.data, rv.data.decode()

    def test_lockdown(self):

        # add a user and try to upload firmware without signing the agreement
        self.login()
        self.add_user("testuser@fwupd.org")
        rv = self.app.post("/lvfs/fsck/lockdown", follow_redirects=True)
        assert b"Disabled all users" in rv.data, rv.data.decode()
        self.logout()
        rv = self._login("testuser@fwupd.org")
        assert b"User account is disabled" in rv.data, rv.data.decode()


if __name__ == "__main__":
    unittest.main()
