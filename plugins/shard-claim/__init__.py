#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2019-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=no-self-use,no-member,too-few-public-methods,unused-argument,singleton-comparison

from lvfs import db
from lvfs.pluginloader import PluginBase
from lvfs.models import Test, ComponentShard, ComponentShardInfo, \
                        ComponentShardClaim, ComponentShardChecksum, Claim

class Plugin(PluginBase):
    def __init__(self, plugin_id=None):
        PluginBase.__init__(self, plugin_id)
        self.name = 'Shard Claim'
        self.summary = 'Add component claims based on shard GUIDs'
        self.order_after = ['uefi-extract']

    def ensure_test_for_fw(self, fw):

        # add if not already exists
        test = fw.find_test_by_plugin_id(self.id)
        if not test:
            test = Test(plugin_id=self.id, waivable=True)
            fw.tests.append(test)

    def run_test_on_md(self, test, md):

        infos_by_guid = {}
        claims_by_csum = {}

        # find any infos that indicate a claim
        for info in db.session.query(ComponentShardInfo)\
                              .filter(ComponentShardInfo.claim_id != None):
            infos_by_guid[info.guid] = info
        for claim in db.session.query(ComponentShardClaim)\
                               .filter(ComponentShardClaim.claim_id != None)\
                               .filter(ComponentShardClaim.checksum != None):
            claims_by_csum[claim.checksum] = claim

        # run analysis on the component and any shards
        for shard in md.shards:
            if shard.guid in infos_by_guid:
                md.add_claim(infos_by_guid[shard.guid].claim)
            if shard.checksum in claims_by_csum:
                md.add_claim(claims_by_csum[shard.checksum].claim)

# run with PYTHONPATH=. ./env/bin/python3 plugins/shard-claim/__init__.py
if __name__ == '__main__':
    import sys
    from lvfs.models import Firmware, Component

    plugin = Plugin('shard-claim')
    _test = Test(plugin_id=plugin.id)
    _fw = Firmware()
    _md = Component()
    _shard = ComponentShard(guid='f114faa8-4fd5-4b95-8bc3-bc5cb5454966')
    _shard.checksums.append(ComponentShardChecksum(kind='SHA256',
                                                   value='fd14d82dd6f4f6fdc3263c25c681b11ef8'\
                                                         'daccd169efcab451cbb32c5f45ef8a'))
    _md.shards.append(_shard)
    _fw.mds.append(_md)
    plugin.run_test_on_md(_test, _md)
    for _claim in _md.claims:
        print(_claim)
