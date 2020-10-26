#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods

import datetime
import functools

from typing import Optional

from flask import g

from sqlalchemy import Column, Integer, Text, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from lvfs import db

from lvfs.dbutils import _execute_count_star
from lvfs.users.models import User


class VendorAffiliationAction(db.Model):

    __tablename__ = "affiliation_actions"

    affiliation_action_id = Column(Integer, primary_key=True)
    affiliation_id = Column(
        Integer, ForeignKey("affiliations.affiliation_id"), nullable=False, index=True
    )
    ctime = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    action = Column(Text, default=None)

    user = relationship("User", foreign_keys=[user_id])
    affiliation = relationship("VendorAffiliation", foreign_keys=[affiliation_id])

    def __repr__(self) -> str:
        return "<VendorAffiliationAction {}>".format(self.action)


class VendorAffiliation(db.Model):

    __tablename__ = "affiliations"

    affiliation_id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    vendor_id = Column(
        Integer, ForeignKey("vendors.vendor_id"), nullable=False, index=True
    )
    vendor_id_odm = Column(
        Integer, ForeignKey("vendors.vendor_id"), nullable=False, index=True
    )

    vendor = relationship(
        "Vendor", foreign_keys=[vendor_id], back_populates="affiliations"
    )
    vendor_odm = relationship("Vendor", foreign_keys=[vendor_id_odm])
    actions = relationship(
        "VendorAffiliationAction", cascade="all,delete,delete-orphan"
    )

    def get_action(self, action: str) -> Optional[VendorAffiliationAction]:
        for act in self.actions:
            if action == act.action:
                return act
        return None

    def __repr__(self) -> str:
        return "VendorAffiliation object %s" % self.affiliation_id


class VendorRestriction(db.Model):

    __tablename__ = "restrictions"

    restriction_id = Column(Integer, primary_key=True)
    vendor_id = Column(
        Integer, ForeignKey("vendors.vendor_id"), nullable=False, index=True
    )
    value = Column(Text, nullable=False)

    vendor = relationship("Vendor", back_populates="restrictions")

    def __repr__(self) -> str:
        return "VendorRestriction object %s" % self.restriction_id


class VendorBranch(db.Model):

    __tablename__ = "vendor_branches"

    branch_id = Column(Integer, primary_key=True)
    vendor_id = Column(
        Integer, ForeignKey("vendors.vendor_id"), nullable=False, index=True
    )
    value = Column(Text, nullable=False)
    ctime = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    vendor = relationship("Vendor", back_populates="branches")
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return "<VendorBranch {}>".format(self.value)


class VendorNamespace(db.Model):

    __tablename__ = "namespaces"

    namespace_id = Column(Integer, primary_key=True)
    vendor_id = Column(
        Integer, ForeignKey("vendors.vendor_id"), nullable=False, index=True
    )
    value = Column(Text, nullable=False)
    ctime = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    vendor = relationship("Vendor", back_populates="namespaces")
    user = relationship("User", foreign_keys=[user_id])

    @property
    def is_valid(self) -> bool:
        if self.value.endswith("."):
            return False
        if self.value.find(".") == -1:
            return False
        return True

    def __repr__(self) -> str:
        return "<VendorNamespace {}>".format(self.value)


class Vendor(db.Model):

    __tablename__ = "vendors"

    vendor_id = Column(Integer, primary_key=True)
    group_id = Column(String(80), nullable=False, index=True)
    display_name = Column(Text, default=None)
    legal_name = Column(Text, default=None)
    internal_team = Column(Text, default=None)
    description = Column(Text, default=None)
    quote_text = Column(Text, default=None)
    quote_author = Column(Text, default=None)
    consulting_text = Column(Text, default=None)
    consulting_link = Column(Text, default=None)
    visible = Column(Boolean, default=False)
    visible_for_search = Column(Boolean, default=False)
    visible_on_landing = Column(Boolean, default=False)
    is_embargo_default = Column(Boolean, default=False)
    comments = Column(Text, default=None)
    icon = Column(Text, default=None)
    keywords = Column(Text, default=None)
    oauth_unknown_user = Column(Text, default=None)
    oauth_domain_glob = Column(Text, default=None)
    remote_id = Column(Integer, ForeignKey("remotes.remote_id"), nullable=False)
    username_glob = Column(Text, default=None)
    verfmt_id = Column(Integer, ForeignKey("verfmts.verfmt_id"))
    url = Column(Text, default=None)
    banned_country_codes = Column(Text, default=None)  # ISO 3166, delimiter ','
    do_not_track = Column(Boolean, default=False)

    users = relationship(
        "User", back_populates="vendor", cascade="all,delete,delete-orphan"
    )
    restrictions = relationship(
        "VendorRestriction", back_populates="vendor", cascade="all,delete,delete-orphan"
    )
    namespaces = relationship(
        "VendorNamespace", back_populates="vendor", cascade="all,delete,delete-orphan"
    )
    branches = relationship(
        "VendorBranch", back_populates="vendor", cascade="all,delete,delete-orphan"
    )
    affiliations = relationship(
        "VendorAffiliation",
        foreign_keys=[VendorAffiliation.vendor_id],
        back_populates="vendor",
        cascade="all,delete,delete-orphan",
    )
    affiliations_for = relationship(
        "VendorAffiliation",
        foreign_keys=[VendorAffiliation.vendor_id_odm],
        back_populates="vendor",
    )
    fws = relationship(
        "Firmware",
        foreign_keys="[Firmware.vendor_id]",
        cascade="all,delete,delete-orphan",
    )
    mdrefs = relationship(
        "ComponentRef",
        foreign_keys="[ComponentRef.vendor_id_partner]",
        cascade="all,delete,delete-orphan",
        back_populates="vendor_partner",
    )
    events = relationship(
        "Event",
        order_by="desc(Event.timestamp)",
        lazy="dynamic",
        cascade="all,delete,delete-orphan",
    )

    verfmt = relationship("Verfmt", foreign_keys=[verfmt_id])
    remote = relationship(
        "Remote",
        foreign_keys=[remote_id],
        single_parent=True,
        cascade="all,delete,delete-orphan",
    )

    @property  # type: ignore
    @functools.lru_cache()
    def fws_stable_recent(self):
        from lvfs.firmware.models import Firmware
        from lvfs.metadata.models import Remote

        now = datetime.datetime.utcnow() - datetime.timedelta(
            weeks=26
        )  # 26 weeks is half a year or about 6 months
        return _execute_count_star(
            db.session.query(Firmware.firmware_id)
            .join(Firmware.remote)
            .filter(
                Remote.name == "stable",
                Firmware.vendor_id == self.vendor_id,
                Firmware.timestamp > now,
            )
        )

    @property  # type: ignore
    @functools.lru_cache()
    def fws_stable(self):
        from lvfs.firmware.models import Firmware
        from lvfs.metadata.models import Remote

        return _execute_count_star(
            db.session.query(Firmware.firmware_id)
            .join(Firmware.remote)
            .filter(Firmware.vendor_id == self.vendor_id, Remote.name == "stable")
        )

    @property  # type: ignore
    @functools.lru_cache()
    def is_odm(self):
        return (
            db.session.query(VendorAffiliation.affiliation_id)
            .filter(VendorAffiliation.vendor_id_odm == self.vendor_id)
            .first()
            is not None
        )

    @property  # type: ignore
    @functools.lru_cache()
    def protocols(self):
        from lvfs.firmware.models import Firmware
        from lvfs.components.models import Component
        from lvfs.metadata.models import Remote
        from lvfs.protocols.models import Protocol

        return (
            db.session.query(Protocol)
            .join(Component)
            .join(Firmware)
            .filter(Firmware.vendor_id == self.vendor_id)
            .join(Remote)
            .filter(Remote.name == "stable")
            .order_by(Protocol.name.asc())
            .all()
        )

    @property
    def is_account_holder(self) -> bool:
        return self.users

    @property
    def should_anonymize(self) -> bool:
        if self.group_id == 'hughski': # this is my hobby; I have no secrets
            return False
        return True

    @property
    def is_unrestricted(self) -> bool:
        for res in self.restrictions:
            if res.value == "*":
                return True
        return False

    @property
    def display_name_with_team(self) -> str:
        if self.internal_team:
            return "{} ({})".format(self.display_name, self.internal_team)
        return self.display_name

    @property
    def ctime(self):
        val = None
        for user in self.users:
            if not user.ctime:
                continue
            if not val or user.ctime < val:
                val = user.ctime
        return val

    @property
    def mtime(self):
        val = None
        for user in self.users:
            if not user.mtime:
                continue
            if not val or user.mtime > val:
                val = user.mtime
        return val

    @property
    def atime(self):
        val = None
        for user in self.users:
            if not user.atime:
                continue
            if not val or user.atime > val:
                val = user.atime
        return val

    def is_affiliate_for(self, vendor_id: int) -> bool:
        for rel in self.affiliations_for:
            if rel.vendor_id == vendor_id:
                return True
        return False

    def is_affiliate(self, vendor_id_odm: int) -> bool:
        for rel in self.affiliations:
            if rel.vendor_id_odm == vendor_id_odm:
                return True
        return False

    def check_acl(self, action: str, user: Optional[User] = None) -> bool:

        # fall back
        if not user:
            user = g.user
        if not user:
            return False
        if user.check_acl("@admin"):
            return True

        # depends on the action requested
        if action == "@upload":
            # all members of a group can upload to that group
            if user.vendor_id == self.vendor_id:
                return True
            # allow vendor affiliates too
            if self.is_affiliate(user.vendor_id):
                return True
            return False
        if action == "@view-metadata":
            # all members of a group can generate the metadata file
            if user.vendor_id == self.vendor_id:
                return True
            return False
        if action == "@manage-users":
            if user.vendor_id != self.vendor_id:
                return False
            # manager user can modify any users in his group
            if user.check_acl("@vendor-manager"):
                return True
            return False
        if action == "@modify-oauth":
            return False
        if action == "@view-affiliations":
            if user.vendor_id != self.vendor_id:
                return False
            return user.check_acl("@vendor-manager")
        if action == "@view-restrictions":
            if user.vendor_id != self.vendor_id:
                return False
            return user.check_acl("@vendor-manager")
        if action == "@modify-affiliations":
            return False
        if action == "@modify-affiliation-actions":
            if user.vendor_id != self.vendor_id:
                return False
            return user.check_acl("@vendor-manager")
        if action == "@view-exports":
            if user.vendor_id != self.vendor_id:
                return False
            return user.check_acl("@qa") or user.check_acl("@vendor-manager")
        if action == "@modify-exports":
            return user.check_acl("@vendor-manager")
        raise NotImplementedError(
            "unknown security check action: %s:%s" % (self, action)
        )

    def __hash__(self) -> int:
        return int(self.vendor_id)

    def __lt__(self, other) -> bool:
        return self.vendor_id < other.vendor_id

    def __eq__(self, other) -> bool:
        return self.vendor_id == other.vendor_id

    def __repr__(self) -> str:
        return "Vendor object %s" % self.group_id
