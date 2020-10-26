#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+

from typing import Any, Dict, List, Optional

from .jcatblob import JcatBlob


class JcatItem:
    def __init__(self, jid: Optional[str] = None):
        self.id = jid
        self.blobs: List[JcatBlob] = []
        self.alias_ids: List[str] = []

    def save(self) -> Dict[str, Any]:
        node: Dict[str, Any] = {}
        node["Id"] = self.id
        if self.alias_ids:
            node["AliasIds"] = self.alias_ids
        if self.blobs:
            node["Blobs"] = [blob.save() for blob in self.blobs]
        return node

    def load(self, node: Dict[str, Any]) -> None:
        self.id = node.get("Id", None)
        if "AliasIds" in node:
            for jid in node["AliasIds"]:
                self.add_alias_id(jid)
        if "Blobs" in node:
            for node_c in node["Blobs"]:
                blob = JcatBlob()
                blob.load(node_c)
                self.blobs.append(blob)

    def add_blob(self, blob: JcatBlob) -> None:
        if blob in self.blobs:
            return
        self.blobs.append(blob)

    def add_alias_id(self, jid: str) -> None:
        if jid in self.alias_ids:
            return
        self.alias_ids.append(jid)

    def __repr__(self) -> str:
        return "JcatItem({})".format(self.id)
