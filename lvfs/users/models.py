#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods,too-many-instance-attributes
# pylint: disable=too-many-arguments,too-many-lines,protected-access

import datetime

from typing import Optional

import onetimepass

from flask import g
from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from lvfs import db


class UserCertificate(db.Model):

    __tablename__ = "certificates"

    certificate_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    ctime = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    serial = Column(String(40), nullable=False)
    text = Column(Text, default=None)

    user = relationship("User", foreign_keys=[user_id])

    def check_acl(self, action: str, user: Optional["User"] = None) -> bool:

        # fall back
        if not user:
            user = g.user
        if not user:
            return False
        if user.check_acl("@admin"):
            return True

        # depends on the action requested
        if action == "@delete":
            if self.user_id == user.user_id:
                return True
            return False
        raise NotImplementedError(
            "unknown security check action: %s:%s" % (self, action)
        )

    def __repr__(self):
        return "UserCertificate object %s" % self.serial


class UserAction(db.Model):

    __tablename__ = "user_actions"

    user_action_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    ctime = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    value = Column(Text, default=None)

    user = relationship("User", foreign_keys=[user_id], back_populates="actions")

    def __repr__(self):
        return "<UserAction {}>".format(self.value)


class User(db.Model):

    __tablename__ = "users"
    __table_args__ = (Index("idx_users_username_password", "username", "password"),)

    user_id = Column(Integer, primary_key=True)
    username = Column(String(80), nullable=False, index=True)
    password_hash = Column("password", String(128), default=None)
    password_ts = Column(DateTime, default=None)
    password_recovery = Column(String(40), default=None)
    password_recovery_ts = Column(DateTime, default=None)
    otp_secret = Column(String(16))
    display_name = Column(Text, default=None)
    vendor_id = Column(
        Integer, ForeignKey("vendors.vendor_id"), nullable=False, index=True
    )
    auth_type = Column(Text, default="disabled")
    auth_warning = Column(Text, default=None)
    is_otp_enabled = Column(Boolean, default=False)
    is_otp_working = Column(Boolean, default=False)
    agreement_id = Column(Integer, ForeignKey("agreements.agreement_id"))
    ctime = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    mtime = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    atime = Column(DateTime, default=None)
    dtime = Column(DateTime, default=None)
    human_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    unused_notify_ts = Column(DateTime, default=None)

    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    agreement = relationship("Agreement", foreign_keys=[agreement_id])
    human_user = relationship("User", remote_side=[user_id])

    fws = relationship(
        "Firmware",
        order_by="desc(Firmware.timestamp)",
        primaryjoin="Firmware.user_id==User.user_id",
    )
    events = relationship(
        "Event",
        order_by="desc(Event.timestamp)",
        lazy="dynamic",
        cascade="all,delete,delete-orphan",
    )
    queries = relationship(
        "YaraQuery",
        order_by="desc(YaraQuery.ctime)",
        cascade="all,delete,delete-orphan",
    )
    certificates = relationship(
        "UserCertificate",
        order_by="desc(UserCertificate.ctime)",
        cascade="all,delete,delete-orphan",
    )
    actions = relationship(
        "UserAction", lazy="joined", cascade="all,delete,delete-orphan"
    )

    def get_action(self, value: str) -> Optional[UserAction]:
        for action in self.actions:
            if action.value == value:
                return action
        return None

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)
        self.password_ts = datetime.datetime.utcnow()

    def verify_password(self, password: str) -> bool:
        # never set, or disabled
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_totp_uri(self) -> str:
        return "otpauth://totp/LVFS:{0}?secret={1}&issuer=LVFS".format(
            self.username, self.otp_secret
        )

    @property
    def needs_2fa(self) -> bool:

        # already done
        if self.is_otp_enabled:
            return False

        # not applicable
        if self.auth_type != "local":
            return False

        # created in the last 1h...
        if (
            datetime.datetime.now() - self.ctime.replace(tzinfo=None)
        ).total_seconds() > 60 * 60:
            return False

        # of required userclass
        return self.check_acl("@admin") or self.check_acl("@vendor-manager")

    def verify_totp(self, token: str) -> bool:
        return onetimepass.valid_totp(token, self.otp_secret)

    def check_acl(self, action: str = None) -> bool:

        # disabled users can do nothing
        if self.auth_type == "disabled":
            return False

        # decide based on the action
        if action in [
            "@qa",
            "@analyst",
            "@vendor-manager",
            "@researcher",
            "@approved-public",
            "@robot",
            "@admin",
            "@partner",
        ]:
            return bool(self.get_action(action[1:]))
        if action == "@view-analytics":
            if self.check_acl("@qa") or self.check_acl("@analyst"):
                return True
            return False
        if action == "@manage-password":
            if self.auth_type == "local":
                return True
            return False
        if action == "@yara-query":
            return self.check_acl("@admin") or self.check_acl("@researcher")
        if action == "@add-action-researcher":
            if not self.vendor.check_acl("@manage-users"):
                return False
            return self.check_acl("@admin") or self.check_acl("@researcher")
        if action == "@add-action-vendor-manager":
            if not self.vendor.check_acl("@manage-users"):
                return False
            return self.check_acl("@admin") or self.check_acl("@vendor-manager")
        if action == "@add-action-partner":
            return self.check_acl("@admin")
        if action == "@add-action-approved-public":
            if not self.vendor.check_acl("@manage-users"):
                return False
            return self.check_acl("@admin") or self.check_acl("@approved-public")
        if action == "@add-action-analyst":
            if not self.vendor.check_acl("@manage-users"):
                return False
            return self.check_acl("@admin") or self.check_acl("@analyst")
        if action == "@add-action-qa":
            if not self.vendor.check_acl("@manage-users"):
                return False
            return self.check_acl("@admin") or self.check_acl("@qa")
        if action == "@add-action-admin":
            if not self.vendor.check_acl("@manage-users"):
                return False
            return self.check_acl("@admin")
        if action == "@add-action-robot":
            return self.vendor.check_acl("@manage-users")
        if action in ("@view-eventlog", "@view-issues"):
            return self.check_acl("@qa")
        raise NotImplementedError(
            "unknown security check type {}: {}".format(action, self)
        )

    def generate_password_recovery(self) -> None:
        from lvfs.util import _generate_password

        if self.check_acl("@robot"):
            raise RuntimeError("account is a robot")
        if self.auth_type == "disabled":
            raise RuntimeError("account is locked")
        if self.auth_type == "local+locked":
            raise RuntimeError("account is locked")
        if self.auth_type == "oauth":
            raise RuntimeError("account set to OAuth only")
        self.mtime = datetime.datetime.utcnow()
        self.password_recovery = _generate_password()
        self.password_recovery_ts = datetime.datetime.utcnow()

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def email_address(self) -> str:
        if self.human_user:
            return self.human_user.username
        return self.username

    @property
    def is_active(self) -> bool:
        return self.auth_type != "disabled"

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return str(self.username)

    def __repr__(self):
        return "User object %s" % self.username
