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


if __name__ == "__main__":
    unittest.main()
