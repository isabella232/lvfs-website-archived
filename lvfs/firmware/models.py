#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods,protected-access,too-many-instance-attributes

import os
import datetime
from typing import Optional, List

from flask import g, url_for

from sqlalchemy import Column, Integer, Text, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from cabarchive import CabArchive

from lvfs import app, db

from lvfs.vendors.models import VendorAffiliation
from lvfs.users.models import User
from lvfs.tests.models import Test
from lvfs.claims.models import Claim
from lvfs.components.models import Component


class FirmwareEvent(db.Model):

    __tablename__ = "firmware_events"

    firmware_event_id = Column(Integer, primary_key=True)
    firmware_id = Column(
        Integer, ForeignKey("firmware.firmware_id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    remote_id = Column(Integer, ForeignKey("remotes.remote_id"), nullable=False)

    fw = relationship("Firmware", back_populates="events")

    user = relationship("User", foreign_keys=[user_id])
    remote = relationship("Remote", foreign_keys=[remote_id], lazy="joined")

    def __repr__(self):
        return "FirmwareEvent object %s" % self.firmware_event_id


class FirmwareLimit(db.Model):

    __tablename__ = "firmware_limits"

    firmware_limit_id = Column(Integer, primary_key=True)
    firmware_id = Column(
        Integer, ForeignKey("firmware.firmware_id"), nullable=False, index=True
    )
    value = Column(Integer, nullable=False)
    user_agent_glob = Column(Text, default=None)
    response = Column(Text, default=None)

    fw = relationship("Firmware", back_populates="limits")


class Firmware(db.Model):

    __tablename__ = "firmware"

    firmware_id = Column(Integer, primary_key=True)
    vendor_id = Column(
        Integer, ForeignKey("vendors.vendor_id"), nullable=False, index=True
    )
    addr = Column(String(40), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    filename = Column(Text, nullable=False)
    download_cnt = Column(Integer, default=0)
    checksum_upload_sha1 = Column(String(40), nullable=False, index=True)
    checksum_upload_sha256 = Column(String(64), nullable=False)
    _version_display = Column("version_display", Text, nullable=True, default=None)
    remote_id = Column(
        Integer, ForeignKey("remotes.remote_id"), nullable=False, index=True
    )
    checksum_signed_sha1 = Column(String(40), nullable=False)
    checksum_signed_sha256 = Column(String(64), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    signed_timestamp = Column(DateTime, default=None)
    is_dirty = Column(Boolean, default=False)  # waiting to be included in metadata
    _banned_country_codes = Column(
        "banned_country_codes", Text, default=None
    )  # ISO 3166, delimiter ','
    report_success_cnt = Column(Integer, default=0)  # updated by cron.py
    report_failure_cnt = Column(Integer, default=0)  # updated by cron.py
    report_issue_cnt = Column(Integer, default=0)  # updated by cron.py
    failure_minimum = Column(Integer, default=0)
    failure_percentage = Column(Integer, default=0)
    _do_not_track = Column("do_not_track", Boolean, default=False)
    vendor_odm_id = Column(
        Integer, ForeignKey("vendors.vendor_id"), nullable=False, index=True
    )
    regenerate_ts = Column(DateTime, default=None)

    mds = relationship(
        "Component",
        back_populates="fw",
        lazy="joined",
        cascade="all,delete,delete-orphan",
    )
    events = relationship(
        "FirmwareEvent",
        order_by="desc(FirmwareEvent.timestamp)",
        back_populates="fw",
        cascade="all,delete,delete-orphan",
    )
    reports = relationship(
        "Report", back_populates="fw", cascade="all,delete,delete-orphan"
    )
    clients = relationship(
        "Client", back_populates="fw", cascade="all,delete,delete-orphan"
    )
    limits = relationship(
        "FirmwareLimit", back_populates="fw", cascade="all,delete,delete-orphan"
    )
    tests = relationship(
        "Test",
        order_by="desc(Test.scheduled_ts)",
        back_populates="fw",
        cascade="all,delete,delete-orphan",
    )
    analytics = relationship(
        "AnalyticFirmware",
        back_populates="firmware",
        cascade="all,delete,delete-orphan",
    )

    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    vendor_odm = relationship("Vendor", foreign_keys=[vendor_odm_id])
    user = relationship("User", foreign_keys=[user_id])
    remote = relationship("Remote", foreign_keys=[remote_id], lazy="joined")

    @property
    def target_duration(self) -> int:
        if not self.events:
            return 0
        return datetime.datetime.utcnow() - self.events[0].timestamp.replace(
            tzinfo=None
        )

    @property
    def release_ts(self) -> Optional[DateTime]:
        for ev in self.events:
            if ev.remote.is_public:
                return ev.timestamp.replace(tzinfo=None)
        return None

    @property
    def do_not_track(self) -> bool:
        return self._do_not_track or self.vendor.do_not_track

    @property
    def is_deleted(self) -> bool:
        return self.remote.is_deleted

    @property
    def is_regenerating(self) -> bool:
        if not self.regenerate_ts:
            return False
        return datetime.datetime.utcnow() < self.regenerate_ts.replace(
            tzinfo=None
        ) + datetime.timedelta(hours=2)

    @property
    def banned_country_codes(self) -> List[str]:
        if self._banned_country_codes:
            return self._banned_country_codes
        return self.vendor.banned_country_codes

    @banned_country_codes.setter
    def banned_country_codes(self, values: List[str]) -> None:
        self._banned_country_codes = ",".join(values)

    @property
    def get_possible_users_to_email(self) -> List[User]:
        users = []

        # vendor that owns the firmware
        for u in self.vendor.users:
            if u.check_acl("@qa") or u.check_acl("@vendor-manager"):
                users.append(u)

        # odm that uploaded the firmware
        if self.vendor != self.vendor_odm:
            for u in self.vendor_odm.users:
                if u.check_acl("@qa") or u.check_acl("@vendor-manager"):
                    users.append(u)
        return users

    @property
    def success(self) -> Optional[int]:
        total = self.report_failure_cnt + self.report_success_cnt
        if not total:
            return None
        return (self.report_success_cnt * 100) / total

    @property
    def success_confidence(self) -> str:
        total = (
            self.report_failure_cnt + self.report_success_cnt + self.report_issue_cnt
        )
        if total > 1000:
            return "high"
        if total > 100:
            return "medium"
        return "low"

    @property
    def filename_absolute(self) -> str:
        if self.is_deleted:
            return os.path.join("/deleted", self.filename)
        return os.path.join("/downloads", self.filename)

    @property
    def color(self) -> str:
        if self.success is None:
            return "secondary"
        if self.success > 95:
            return "success"
        if self.success > 80:
            return "warning"
        return "danger"

    @property
    def names(self) -> List[str]:
        names: List[str] = []
        for md in self.mds:
            if md.names:
                names.extend(md.names)
        return names

    @property
    def is_failure(self) -> bool:
        if not self.report_failure_cnt:
            return False
        if not self.failure_minimum:
            return False
        if not self.failure_percentage:
            return False
        if self.report_failure_cnt < self.failure_minimum:
            return False
        return self.success < self.failure_percentage

    @property
    def inhibit_download(self) -> bool:
        for md in self.mds:
            if md.inhibit_download:
                return True
        return False

    def find_test_by_plugin_id(self, plugin_id: str) -> Optional[Test]:
        for test in self.tests:
            if test.plugin_id == plugin_id:
                return test
        return None

    @property
    def autoclaims(self) -> List[Claim]:
        # return the smallest of all the components, i.e. the least secure
        md_lowest = None
        claims = []
        for md in self.mds:
            if not md_lowest or md.security_level < md_lowest.security_level:
                md_lowest = md
                claims = md.autoclaims

        # been virus checked
        test = self.find_test_by_plugin_id("clamav")
        if test and test.ended_ts and test.success:
            claims.append(
                Claim(
                    kind="virus-safe",
                    icon="success",
                    summary="Virus checked using ClamAV",
                    url="https://lvfs.readthedocs.io/en/latest/claims.html#virus-safe",
                )
            )
        return claims

    @property
    def claims(self) -> List[Claim]:
        claims: List[Claim] = []
        for md in self.mds:
            for claim in md.claims:
                if claim not in claims:
                    claims.append(claim)
        return claims

    @property
    def scheduled_signing(self) -> DateTime:
        now = datetime.datetime.now()
        secs = ((5 - (now.minute % 5)) * 60) + (60 - now.second)
        return datetime.datetime.now() + datetime.timedelta(seconds=secs)

    @property
    def version_display(self) -> str:
        if self._version_display:
            return self._version_display
        md_versions: List[str] = []
        for md in self.mds:
            if not md.version_display:
                continue
            if md.version_display not in md_versions:
                md_versions.append(md.version_display)
        return ", ".join(md_versions)

    @version_display.setter
    def version_display(self, value):
        self._version_display = value

    @property
    def md_prio(self) -> Optional[Component]:
        md_prio = None
        for md in self.mds:
            if not md_prio or md.priority > md_prio.priority:
                md_prio = md
        return md_prio

    @property
    def problems(self) -> List[Claim]:
        # does the firmware have any warnings
        problems = []
        if self.is_deleted:
            problems.append(
                Claim(
                    kind="deleted",
                    icon="trash",
                    summary="Firmware has been deleted",
                    description="Once a file has been deleted on the LVFS it must be "
                    "undeleted before it can be moved to a different target.",
                    url=url_for("firmware.route_show", firmware_id=self.firmware_id),
                )
            )
        if not self.signed_timestamp:
            problems.append(
                Claim(
                    kind="unsigned",
                    icon="waiting",
                    summary="Firmware is unsigned",
                    description="Signing a firmware file on the LVFS is automatic and will "
                    "be completed soon.\n"
                    "You can refresh this page to find out when the firmware "
                    "has been signed.",
                    url=url_for("firmware.route_show", firmware_id=self.firmware_id),
                )
            )
        # test failures
        for test in self.tests:
            if not test.started_ts:
                problems.append(
                    Claim(
                        kind="test-pending",
                        icon="waiting",
                        summary="Runtime test {} is pending".format(test.plugin_id),
                        description="The LVFS runs tests on certain types of firmware to check they "
                        "are valid.\n"
                        "Some tests are still pending and will be completed shortly.\n"
                        "You can refresh this page to find out when the firmware has "
                        "been tested.",
                        url=url_for(
                            "firmware.route_tests", firmware_id=self.firmware_id
                        ),
                    )
                )
            elif not test.success and not test.waived_ts:
                if test.waivable:
                    problems.append(
                        Claim(
                            kind="test-failed",
                            icon="warning",
                            summary="Runtime test {} did not succeed".format(
                                test.plugin_id
                            ),
                            description="A check on the firmware has failed.\n"
                            "This failure can be waived by a QA user and ignored.",
                            url=url_for(
                                "firmware.route_tests", firmware_id=self.firmware_id
                            ),
                        )
                    )
                else:
                    problems.append(
                        Claim(
                            kind="test-failed",
                            icon="warning",
                            summary="Runtime test {} did not succeed".format(
                                test.plugin_id
                            ),
                            description="A non-waivable check on the firmware has failed.",
                            url=url_for(
                                "firmware.route_tests", firmware_id=self.firmware_id
                            ),
                        )
                    )
        for md in self.mds:
            for problem in md.problems:
                problem.md = md
                problems.append(problem)
        return problems

    def _is_owner(self, user) -> bool:
        return self.user_id == user.user_id

    @property
    def absolute_path(self) -> str:
        if self.is_deleted:
            return os.path.join(app.config["RESTORE_DIR"], self.filename)
        return os.path.join(app.config["DOWNLOAD_DIR"], self.filename)

    def _ensure_blobs(self) -> None:
        with open(self.absolute_path, "rb") as f:
            cabarchive = CabArchive(f.read())
        for md in self.mds:
            try:
                md._blob = cabarchive[md.filename_contents].buf
            except KeyError as _:
                pass

    def _is_vendor(self, user) -> bool:
        return self.vendor_id == user.vendor_id

    def _is_odm(self, user) -> bool:
        return self.vendor_odm.vendor_id == user.vendor_id

    def mark_dirty(self) -> None:
        self.is_dirty = True
        self.remote.is_dirty = True

    def _is_permitted_action(self, action: str, user: User) -> bool:

        # is vendor
        if self._is_vendor(user):
            return True

        # the user is not a member of the ODM vendor
        if self.vendor_odm.vendor_id != user.vendor.vendor_id:
            return False

        # check ODM permissions
        aff = (
            db.session.query(VendorAffiliation)
            .filter(VendorAffiliation.vendor_id == self.vendor_id)
            .filter(VendorAffiliation.vendor_id_odm == user.vendor_id)
            .first()
        )
        if not aff:
            return False
        return aff.get_action(action)

    def check_acl(self, action: str, user: Optional[User] = None) -> bool:

        # fall back
        if not user:
            user = g.user
        if not user:
            return False
        if user.check_acl("@admin"):
            return True

        # depends on the action requested
        if action == "@delete":
            if self.is_deleted:
                return False
            if user.check_acl("@qa") and self._is_permitted_action(action, user):
                return True
            return False
        if action == "@nuke":
            if not self.is_deleted:
                return False
            return False
        if action == "@view":
            if user.check_acl("@qa") and self._is_permitted_action(action, user):
                return True
            if user.check_acl("@analyst") and self._is_permitted_action(action, user):
                return True
            if self._is_owner(user):
                return True
            return False
        if action == "@view-analytics":
            if not self.check_acl("@view", user):
                return False
            if user.check_acl("@qa") or user.check_acl("@analyst"):
                return True
            return False
        if action == "@undelete":
            if user.check_acl("@qa") and self._is_permitted_action(action, user):
                return True
            if self._is_owner(user):
                return True
            return False
        if action == "@resign":
            if user.check_acl("@qa") and self._is_permitted_action(action, user):
                return True
            if self._is_owner(user):
                return True
            return False
        if action in ("@promote-stable", "@promote-testing"):
            if user.check_acl("@approved-public") and self._is_permitted_action(
                action, user
            ):
                return True
            return False
        if action.startswith("@promote-"):
            if user.check_acl("@qa") and self._is_vendor(user):
                return True
            # ODM vendor can always move private<->embargo
            if self._is_odm(user):
                old = self.remote.name
                if old.startswith("embargo-"):
                    old = "embargo"
                new = action[9:]
                if new.startswith("embargo-"):
                    new = "embargo"
                if old in ("private", "embargo") and new in ("private", "embargo"):
                    return True
            return False
        if action == "@modify":
            if user.check_acl("@qa") and self._is_permitted_action(action, user):
                return True
            if self._is_owner(user):
                return True
            return False
        if action == "@modify-limit":
            if user.check_acl("@qa") and self._is_permitted_action(action, user):
                return True
            return False
        if action == "@modify-affiliation":
            if user.check_acl("@qa") and self._is_permitted_action(action, user):
                return True
            return False
        raise NotImplementedError(
            "unknown security check action: %s:%s" % (self, action)
        )

    def __repr__(self):
        return "Firmware object %s" % self.checksum_upload_sha1
