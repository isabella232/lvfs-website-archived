#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods,protected-access,too-many-instance-attributes,too-many-lines

import os
import collections
import math
import hashlib
import zlib
from typing import Optional, List, Dict
from distutils.version import StrictVersion

from flask import g, url_for

from sqlalchemy import (
    Column,
    Integer,
    Text,
    String,
    DateTime,
    Boolean,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy

from pkgversion import vercmp

from lvfs import app, db

from lvfs.claims.models import Claim
from lvfs.users.models import User
from lvfs.vendors.models import VendorTag
from lvfs.util import _split_search_string, _sanitize_keyword


class ComponentShardInfo(db.Model):

    __tablename__ = "component_shard_infos"

    component_shard_info_id = Column(Integer, primary_key=True)
    guid = Column(String(36), default=None, index=True)
    description = Column(Text, default=None)
    cnt = Column(Integer, default=0)
    claim_id = Column(Integer, ForeignKey("claims.claim_id"), nullable=True, index=True)

    shards = relationship("ComponentShard", cascade="all,delete,delete-orphan")
    claim = relationship("Claim")

    def __repr__(self) -> str:
        return "ComponentShardInfo object %s" % self.component_shard_info_id


class ComponentShardChecksum(db.Model):

    __tablename__ = "component_shard_checksums"

    checksum_id = Column(Integer, primary_key=True)
    component_shard_id = Column(
        Integer,
        ForeignKey("component_shards.component_shard_id"),
        nullable=False,
        index=True,
    )
    kind = Column(Text, nullable=False, default=None)
    value = Column(Text, nullable=False, default=None)

    shard = relationship("ComponentShard")

    def __repr__(self) -> str:
        return "ComponentShardChecksum object %s(%s)" % (self.kind, self.value)


class ComponentShardCertificate(db.Model):

    __tablename__ = "component_shard_certificates"

    component_shard_certificate_id = Column(Integer, primary_key=True)
    component_shard_id = Column(
        Integer,
        ForeignKey("component_shards.component_shard_id"),
        nullable=False,
        index=True,
    )
    kind = Column(Text, default=None)
    plugin_id = Column(Text, default=None)
    description = Column(Text, default=None)
    serial_number = Column(Text, default=None)
    not_before = Column(DateTime, default=None)
    not_after = Column(DateTime, default=None)

    shard = relationship("ComponentShard", back_populates="certificates")

    @property
    def color(self) -> str:
        if self.not_before and self.not_before > self.shard.md.fw.timestamp:
            return "danger"
        if self.not_after and self.not_after < self.shard.md.fw.timestamp:
            return "danger"
        return "success"

    def __repr__(self) -> str:
        data: List[str] = []
        if self.serial_number:
            data.append("serial_number:{}".format(self.serial_number))
        if self.not_before:
            data.append("not_before:{}".format(self.not_before))
        if self.not_after:
            data.append("not_after:{}".format(self.not_after))
        if self.description:
            data.append("desc:{}".format(self.description))
        return "ComponentShardCertificate ({})".format(", ".join(data))


def _calculate_entropy(s: bytes) -> float:
    probabilities = [n_x / len(s) for x, n_x in collections.Counter(s).items()]
    e_x = [-p_x * math.log(p_x, 2) for p_x in probabilities]
    return sum(e_x)


class ComponentShardClaim(db.Model):

    __tablename__ = "component_shard_claims"

    component_shard_claim_id = Column(Integer, primary_key=True)
    component_shard_info_id = Column(
        Integer, ForeignKey("component_shard_infos.component_shard_info_id")
    )
    checksum = Column(Text, nullable=False, default=None)
    claim_id = Column(Integer, ForeignKey("claims.claim_id"), nullable=True)

    info = relationship("ComponentShardInfo")
    claim = relationship("Claim")

    def __repr__(self) -> str:
        return "ComponentShardClaim object {},{} -> {}({})".format(
            self.info.guid, self.checksum, self.kind, self.value
        )


class ComponentShardAttribute(db.Model):
    __tablename__ = "component_shard_attributes"

    component_shard_attribute_id = Column(Integer, primary_key=True)
    component_shard_id = Column(
        Integer,
        ForeignKey("component_shards.component_shard_id"),
        nullable=False,
        index=True,
    )
    key = Column(Text, nullable=False)
    value = Column(Text, default=None)

    component_shard = relationship("ComponentShard", back_populates="attributes")

    def __repr__(self) -> str:
        return "ComponentShardAttribute object %s=%s" % (self.key, self.value)


class ComponentShard(db.Model):

    __tablename__ = "component_shards"

    component_shard_id = Column(Integer, primary_key=True)
    component_id = Column(
        Integer, ForeignKey("components.component_id"), nullable=False, index=True
    )
    component_shard_info_id = Column(
        Integer,
        ForeignKey("component_shard_infos.component_shard_info_id"),
        default=None,
    )
    plugin_id = Column(Text, default=None)
    guid = Column(String(36), default=None, index=True)
    name = Column(Text, default=None)
    size = Column(Integer, default=0)
    entropy = Column(Float, default=0.0)

    checksums = relationship(
        "ComponentShardChecksum",
        back_populates="shard",
        cascade="all,delete,delete-orphan",
    )
    certificates = relationship(
        "ComponentShardCertificate",
        order_by="desc(ComponentShardCertificate.component_shard_certificate_id)",
        back_populates="shard",
        cascade="all,delete,delete-orphan",
    )
    info = relationship("ComponentShardInfo")
    yara_query_results = relationship(
        "YaraQueryResult", cascade="all,delete,delete-orphan"
    )

    md = relationship("Component", back_populates="shards")
    attributes = relationship(
        "ComponentShardAttribute",
        back_populates="component_shard",
        cascade="all,delete,delete-orphan",
    )

    def get_attr_value(self, key: str) -> Optional[str]:
        for attr in self.attributes:
            if attr.key == key:
                return attr.value
        return None

    @property
    def description(self) -> Optional[str]:
        if self.info.description:
            return self.info.description
        if self.name.endswith("Pei"):
            return "The Pre-EFI Initialization phase is invoked early in the boot flow."
        if self.name.endswith("Dxe"):
            return "The Driver Execution Environment phase is where most of the system \
                    initialization is performed."
        return None

    @property
    def blob(self) -> Optional[bytes]:
        if not hasattr(self, "_blob"):
            # restore from disk if available
            fn = self.absolute_path
            if not os.path.exists(fn):
                return None
            with open(fn, "rb") as f:
                self._blob = zlib.decompressobj().decompress(f.read())
        return self._blob

    @blob.setter
    def blob(self, value: bytes):
        self._blob = value

    @property
    def checksum(self) -> Optional[str]:
        for csum in self.checksums:
            if csum.kind == "SHA256":
                return csum.value
        return None

    def set_blob(self, value: bytes, checksums: Optional[List[str]] = None) -> None:
        """ Set data blob and add checksum objects """
        self._blob = value
        self.size = len(value)
        self.entropy = _calculate_entropy(value)

        # default fallback
        if not checksums:
            checksums = ["SHA1", "SHA256"]

        # SHA1 is what's used by researchers, but considered broken
        if "SHA1" in checksums:
            csum = ComponentShardChecksum(
                value=hashlib.sha1(value).hexdigest(), kind="SHA1"
            )
            self.checksums.append(csum)

        # SHA256 is now the best we have
        if "SHA256" in checksums:
            csum = ComponentShardChecksum(
                value=hashlib.sha256(value).hexdigest(), kind="SHA256"
            )
            self.checksums.append(csum)

    @property
    def absolute_path(self) -> str:
        return os.path.join(app.config["SHARD_DIR"], str(self.component_id), self.name)

    def save(self):
        fn = self.absolute_path
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        with open(fn, "wb") as f:
            f.write(zlib.compress(self._blob))

    def __repr__(self) -> str:
        return "ComponentShard object %s" % self.component_shard_id


class ComponentIssue(db.Model):

    __tablename__ = "component_issues"

    component_issue_id = Column(Integer, primary_key=True)
    component_id = Column(
        Integer, ForeignKey("components.component_id"), nullable=False, index=True
    )
    kind = Column(Text, nullable=False)
    value = Column(Text, nullable=False)

    md = relationship("Component", back_populates="issues")

    @property
    def url(self) -> Optional[str]:
        if self.kind == "cve":
            return "https://nvd.nist.gov/vuln/detail/{}".format(self.value)
        if self.kind == "dell":
            # you have to search for the issue number yourself...
            return "https://www.dell.com/support/security/en-us/"
        if self.kind == "lenovo":
            return "https://support.lenovo.com/us/en/product_security/{}".format(
                self.value
            )
        if self.kind == "intel" and self.value.startswith("INTEL-SA-"):
            return "https://www.intel.com/content/www/us/en/security-center/advisory/{}".format(
                self.value
            )
        return None

    @property
    def problem(self) -> Optional[Claim]:
        if self.kind == "cve":
            parts = self.value.split("-")
            if len(parts) != 3 or parts[0] != "CVE":
                return Claim(
                    kind="invalid-issue",
                    icon="warning",
                    summary="Invalid component issue",
                    description="Format expected to be CVE-XXXX-XXXXX",
                )
            if not parts[1].isnumeric or int(parts[1]) < 1995:
                return Claim(
                    kind="invalid-issue",
                    icon="warning",
                    summary="Invalid component issue",
                    description="Invalid year in CVE value",
                )
            if not parts[2].isnumeric:
                return Claim(
                    kind="invalid-issue",
                    icon="warning",
                    summary="Invalid component issue",
                    description="Expected integer in CVE token",
                )
            return None
        if self.kind == "dell":
            parts = self.value.split("-")
            if len(parts) != 3 or parts[0] != "DSA":
                return Claim(
                    kind="invalid-issue",
                    icon="warning",
                    summary="Invalid component issue",
                    description="Format expected to be DSA-XXXX-XXX",
                )
            if not parts[1].isnumeric or int(parts[1]) < 1995:
                return Claim(
                    kind="invalid-issue",
                    icon="warning",
                    summary="Invalid component issue",
                    description="Invalid year in DSA value",
                )
            if not parts[2].isnumeric:
                return Claim(
                    kind="invalid-issue",
                    icon="warning",
                    summary="Invalid component issue",
                    description="Expected integer in DSA token",
                )
            return None
        if self.kind == "lenovo":
            parts = self.value.split("-")
            if len(parts) != 2 or parts[0] != "LEN":
                return Claim(
                    kind="invalid-issue",
                    icon="warning",
                    summary="Invalid component issue",
                    description="Format expected to be LEN-XXXXX",
                )
            if not parts[1].isnumeric:
                return Claim(
                    kind="invalid-issue",
                    icon="warning",
                    summary="Invalid component issue",
                    description="Expected integer in LEN token",
                )
            return None
        if self.kind == "intel":
            parts = self.value.split("-")
            if len(parts) != 3 or parts[0] != "INTEL" or parts[1] not in ["SA", "TA"]:
                return Claim(
                    kind="invalid-issue",
                    icon="warning",
                    summary="Invalid component issue",
                    description="Format expected to be INTEL-XA-XXXXX",
                )
            if not parts[2].isnumeric:
                return Claim(
                    kind="invalid-issue",
                    icon="warning",
                    summary="Invalid component issue",
                    description="Expected integer in INTEL-XA token",
                )
            return None
        return Claim(
            kind="invalid-issue",
            icon="warning",
            summary="Invalid component kind",
            description="Issue kind {} not supported".format(self.kind),
        )

    def __repr__(self) -> str:
        return "<ComponentIssue {}>".format(self.value)


def _is_valid_url(url: str) -> bool:
    if not url.startswith("https://") and not url.startswith("http://"):
        return False
    return True


class ComponentClaim(db.Model):

    __tablename__ = "component_claims"

    component_claim_id = Column(Integer, primary_key=True)
    component_id = Column(
        Integer, ForeignKey("components.component_id"), nullable=False, index=True
    )
    claim_id = Column(
        Integer, ForeignKey("claims.claim_id"), nullable=False, index=True
    )

    md = relationship("Component", back_populates="component_claims")
    claim = relationship("Claim")

    def __repr__(self) -> str:
        return "<ComponentClaim {}>".format(self.component_claim_id)


class ComponentRef(db.Model):

    __tablename__ = "component_refs"

    component_ref_id = Column(Integer, primary_key=True)
    component_id = Column(Integer, ForeignKey("components.component_id"), index=True)
    vendor_id = Column(
        Integer, ForeignKey("vendors.vendor_id"), nullable=False, index=True
    )
    vendor_id_partner = Column(
        Integer, ForeignKey("vendors.vendor_id"), nullable=False, index=True
    )
    protocol_id = Column(Integer, ForeignKey("protocol.protocol_id"))
    appstream_id = Column(Text, default=None)
    version = Column(Text, nullable=False)
    release_tag = Column(Text, default=None)
    date = Column(DateTime, default=None)
    name = Column(Text, nullable=False)
    url = Column(Text, default=None)
    status = Column(Text)

    md = relationship("Component")
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    vendor_partner = relationship(
        "Vendor", foreign_keys=[vendor_id_partner], back_populates="mdrefs"
    )
    protocol = relationship("Protocol")

    def __lt__(self, other) -> bool:
        return vercmp(self.version, other.version) < 0

    def __eq__(self, other) -> bool:
        return vercmp(self.version, other.version) == 0

    @property
    def version_with_tag(self) -> str:
        if self.release_tag:
            return "{} ({})".format(self.release_tag, self.version)
        return self.version

    def __repr__(self) -> str:
        return "<ComponentRef {}>".format(self.version)


class Component(db.Model):

    __tablename__ = "components"

    _blob: Optional[bytes] = None

    component_id = Column(Integer, primary_key=True)
    firmware_id = Column(
        Integer, ForeignKey("firmware.firmware_id"), nullable=False, index=True
    )
    protocol_id = Column(Integer, ForeignKey("protocol.protocol_id"))
    category_id = Column(Integer, ForeignKey("categories.category_id"))
    checksum_contents_sha1 = Column(String(40), nullable=False)
    checksum_contents_sha256 = Column(String(64), nullable=False)
    appstream_id = Column(Text, nullable=False)
    branch = Column(Text, default=None)
    name = Column(Text, default=None)
    name_variant_suffix = Column(Text, default=None)
    summary = Column(Text, default=None)
    icon = Column(Text, default=None)
    description = Column(Text, default=None)  # markdown format
    release_description = Column(Text, default=None)  # markdown format
    details_url = Column(Text, default=None)
    source_url = Column(Text, default=None)
    url_homepage = Column(Text, default=None)
    metadata_license = Column(Text, default=None)
    project_license = Column(Text, default=None)
    developer_name = Column(Text, default=None)
    filename_contents = Column(Text, nullable=False)
    filename_xml = Column(Text, nullable=False)
    release_timestamp = Column(Integer, default=0)
    version = Column(Text, nullable=False)
    release_installed_size = Column(Integer, default=0)
    release_download_size = Column(Integer, default=0)
    release_urgency = Column(Text, default=None)
    release_tag = Column(Text, default=None)
    release_message = Column(Text, default=None)  # LVFS::UpdateMessage
    release_image = Column(Text, default=None)  # LVFS::UpdateImage
    release_image_safe = Column(Text, default=None)
    screenshot_url = Column(Text, default=None)
    screenshot_url_safe = Column(Text, default=None)
    screenshot_caption = Column(Text, default=None)
    inhibit_download = Column(Boolean, default=False)
    verfmt_id = Column(Integer, ForeignKey("verfmts.verfmt_id"))
    priority = Column(Integer, default=0)
    install_duration = Column(Integer, default=0)

    fw = relationship("Firmware", back_populates="mds", lazy="joined")
    requirements = relationship(
        "ComponentRequirement", back_populates="md", cascade="all,delete,delete-orphan"
    )
    issues = relationship(
        "ComponentIssue", back_populates="md", cascade="all,delete,delete-orphan"
    )
    component_claims = relationship(
        "ComponentClaim", back_populates="md", cascade="all,delete,delete-orphan"
    )
    issue_values = association_proxy("issues", "value")
    device_checksums = relationship(
        "ComponentChecksum", back_populates="md", cascade="all,delete,delete-orphan"
    )
    guids = relationship(
        "ComponentGuid",
        back_populates="md",
        lazy="joined",
        cascade="all,delete,delete-orphan",
    )
    shards = relationship(
        "ComponentShard",
        order_by="desc(ComponentShard.component_shard_id)",
        back_populates="md",
        cascade="all,delete,delete-orphan",
    )
    keywords = relationship(
        "ComponentKeyword", back_populates="md", cascade="all,delete,delete-orphan"
    )
    mdrefs = relationship(
        "ComponentRef", back_populates="md", cascade="all,delete,delete-orphan"
    )
    protocol = relationship("Protocol", foreign_keys=[protocol_id])
    category = relationship("Category", foreign_keys=[category_id])
    verfmt = relationship("Verfmt", foreign_keys=[verfmt_id])
    yara_query_results = relationship(
        "YaraQueryResult", lazy="joined", cascade="all,delete,delete-orphan"
    )

    def __lt__(self, other) -> bool:
        return vercmp(self.version_display, other.version_display) < 0

    def __eq__(self, other) -> bool:
        return vercmp(self.version_display, other.version_display) == 0

    def _vendor_tag_with_attr(self, attr: Optional[str] = None) -> Optional[VendorTag]:

        # category match
        if self.category:
            for tag in self.fw.vendor.tags:
                if attr and not getattr(tag, attr):
                    continue
                if tag.category_id == self.category_id:
                    return tag
                if (
                    self.category.fallback
                    and tag.category_id == self.category.fallback.category_id
                ):
                    return tag

        # the 'any' category
        for tag in self.fw.vendor.tags:
            if attr and not getattr(tag, attr):
                continue
            if not tag.category:
                return tag

        # failed
        return None

    @property
    def vendor_tag(self) -> Optional[VendorTag]:
        return self._vendor_tag_with_attr()

    @property
    def icon_with_fallback(self) -> Optional[str]:
        if self.icon:
            return self.icon
        if self.protocol and self.protocol.icon:
            return self.protocol.icon
        if self.category and self.category.icon:
            return self.category.icon
        if self.category and self.category.fallback and self.category.fallback.icon:
            return self.category.fallback.icon
        return None

    @property
    def details_url_with_fallback(self) -> Optional[str]:

        # set explicitly
        if self.details_url:
            return self.details_url

        # get tag for category
        tag = self._vendor_tag_with_attr("details_url")
        if not tag:
            return None

        # return with string substitutions; if not set then return invalid
        details_url = tag.details_url
        replacements: Dict[str, str] = {
            "$RELEASE_TAG$": self.release_tag,
            "$VERSION$": self.version_display,
        }
        for key in replacements:
            if details_url.find(key) != -1:
                if not replacements[key]:
                    return None
                details_url = details_url.replace(key, replacements[key])

        # success
        return details_url

    @property
    def blob(self) -> Optional[bytes]:
        if not hasattr(self, "_blob") or not self._blob:
            self._blob = None
            self.fw._ensure_blobs()
        return self._blob

    @blob.setter
    def blob(self, value: Optional[bytes]):
        self._blob = value

    @property
    def names(self) -> Optional[List[str]]:
        if not self.name:
            return None
        return self.name.split("/")

    @property
    def appstream_id_prefix(self) -> str:
        sections = self.appstream_id.split(".", maxsplit=4)
        return ".".join(sections[:2])

    @property
    def certificates(self) -> List[ComponentShardCertificate]:
        certs: List[ComponentShardCertificate] = []
        for shard in self.shards:
            certs.extend(shard.certificates)
        return certs

    @property
    def name_with_category(self) -> str:
        name = self.name
        if self.name_variant_suffix:
            name += " (" + self.name_variant_suffix + ")"
        if self.category:
            if self.category.name:
                name += " " + self.category.name
            else:
                name += " " + self.category.value
        return name

    @property
    def name_with_vendor(self) -> str:
        name = self.fw.vendor.display_name + " " + self.name
        if self.name_variant_suffix:
            name += " (" + self.name_variant_suffix + ")"
        return name

    @property
    def developer_name_display(self) -> Optional[str]:
        if not self.developer_name:
            return None
        tmp = str(self.developer_name)
        for suffix in [" Limited", " Ltd.", " Inc.", " Corp"]:
            if tmp.endswith(suffix):
                return tmp[: -len(suffix)]
        return tmp

    @property
    def claims(self) -> List[Claim]:
        return [component_claim.claim for component_claim in self.component_claims]

    @property
    def autoclaims(self) -> List[Claim]:
        claims: List[Claim] = []
        if self.protocol:
            if self.protocol.is_signed:
                claims.append(
                    Claim(
                        kind="signed-firmware",
                        icon="success",
                        summary="Update is cryptographically signed",
                        url="https://lvfs.readthedocs.io/en/latest/claims.html#signed-firmware",
                    )
                )
            else:
                claims.append(
                    Claim(
                        kind="no-signed-firmware",
                        icon="warning",
                        summary="Update is not cryptographically signed",
                        url="https://lvfs.readthedocs.io/en/latest/claims.html#signed-firmware",
                    )
                )
            if self.protocol.can_verify:
                claims.append(
                    Claim(
                        kind="verify-firmware",
                        icon="success",
                        summary="Firmware can be verified after flashing",
                        url="https://lvfs.readthedocs.io/en/latest/claims.html#verified-firmware",
                    )
                )
                if self.category and self.category.expect_device_checksum:
                    if self.device_checksums:
                        claims.append(
                            Claim(
                                kind="device-checksum",
                                icon="success",
                                summary="Firmware has attestation checksums",
                                url="https://lvfs.readthedocs.io/en/latest/claims.html#device-checksums",
                            )
                        )
                    else:
                        claims.append(
                            Claim(
                                kind="no-device-checksum",
                                icon="warning",
                                summary="Firmware has no attestation checksums",
                                url="https://lvfs.readthedocs.io/en/latest/claims.html#device-checksums",
                            )
                        )
            else:
                claims.append(
                    Claim(
                        kind="no-verify-firmware",
                        icon="warning",
                        summary="Firmware cannot be verified after flashing",
                        url="https://lvfs.readthedocs.io/en/latest/claims.html#verified-firmware",
                    )
                )
        if self.checksum_contents_sha1:
            claims.append(
                Claim(
                    kind="vendor-provenance",
                    icon="success",
                    summary="Added to the LVFS by {}".format(
                        self.fw.vendor.display_name
                    ),
                    url="https://lvfs.readthedocs.io/en/latest/claims.html#vendor-provenance",
                )
            )
        if self.source_url:
            claims.append(
                Claim(
                    kind="source-url",
                    icon="success",
                    summary="Source code available",
                    url="https://lvfs.readthedocs.io/en/latest/claims.html#source-url",
                )
            )
        return claims

    @property
    def security_level(self) -> int:
        claims: Dict[str, Claim] = {}
        for claim in self.autoclaims:
            claims[claim.kind] = claim
        if "signed-firmware" in claims and "device-checksum" in claims:
            return 2
        if "signed-firmware" in claims:
            return 1
        return 0

    @property
    def requires_source_url(self) -> bool:
        if self.project_license.find("GPL") != -1:
            return True
        return False

    @property
    def version_with_tag(self) -> str:
        if self.release_tag:
            return "{} ({})".format(self.release_tag, self.version_display)
        return self.version_display

    @property
    def version_display(self) -> str:
        if self.version.isdigit():
            if self.verfmt:
                return self.verfmt._uint32_to_str(int(self.version))
        return self.version

    @property
    def version_sections(self) -> int:
        if not self.version_display:
            return 0
        return len(self.version_display.split("."))

    @property
    def problems(self) -> List[Claim]:

        # verify update description
        if self.release_description:
            from lvfs.util import _xml_from_markdown
            from lvfs.claims.utils import _get_update_description_problems

            root = _xml_from_markdown(self.release_description)
            problems = _get_update_description_problems(root)
            # check for OEMs just pasting in the XML like before
            for element_name in ["p", "li", "ul", "ol"]:
                if self.release_description.find("<" + element_name + ">") != -1:
                    problems.append(
                        Claim(
                            kind="invalid-release-description",
                            icon="warning",
                            summary="No valid update description",
                            description="Release description cannot contain XML markup",
                        )
                    )
                    break
        else:
            problems = []
            problems.append(
                Claim(
                    kind="no-release-description",
                    icon="warning",
                    summary="Release description is missing",
                    description="All components should have a suitable update "
                    "description before a firmware is moved to stable.\n"
                    "Writing good quality release notes are really important "
                    "as some users may be worried about an update that does "
                    "not explain what it fixes.\n"
                    "This also can be set in the .metainfo.xml file.",
                )
            )

        # urgency is now a hard requirement
        if self.release_urgency == "unknown":
            problems.append(
                Claim(
                    kind="no-release-urgency",
                    icon="warning",
                    summary="Release urgency has not been set",
                    description="All components should have an appropriate "
                    "update urgency before a firmware is moved to stable.\n"
                    "This also can be set in the .metainfo.xml file.",
                )
            )

        # release timestamp is now a hard requirement
        if self.release_timestamp == 0:
            problems.append(
                Claim(
                    kind="no-release-timestamp",
                    icon="warning",
                    summary="Release timestamp was not set",
                    description="All components should have an appropriate "
                    "update timestamp at upload time.\n"
                    "This also can be set in the .metainfo.xml file.",
                )
            )

        # we are going to be making policy decision on this soon
        if not self.protocol or self.protocol.value == "unknown":
            problems.append(
                Claim(
                    kind="no-protocol",
                    icon="warning",
                    summary="Update protocol has not been set",
                    description="All components should have a defined update protocol "
                    "before being moved to stable.\n"
                    "This also can be set in the .metainfo.xml file.",
                    url=url_for(
                        "components.route_show", component_id=self.component_id
                    ),
                )
            )

        # check the GUIDs are indeed lowercase GUIDs (already done on upload)
        for guid in self.guids:
            from lvfs.util import _validate_guid

            if not _validate_guid(guid.value):
                problems.append(
                    Claim(
                        kind="invalid-guid",
                        icon="warning",
                        summary="Component GUID invalid",
                        description="GUID {} is not valid".format(guid.value),
                        url=url_for(
                            "components.route_show", component_id=self.component_id
                        ),
                    )
                )

        # check the version matches the expected section count
        if self.verfmt and self.verfmt.value != "plain" and self.verfmt.sections:
            if self.version_sections != self.verfmt.sections:
                problems.append(
                    Claim(
                        kind="invalid-version-for-format",
                        icon="warning",
                        summary="Version format invalid",
                        description="The version number {} incompatible with {}.".format(
                            self.version_display, self.verfmt.value
                        ),
                        url=url_for(
                            "components.route_show", component_id=self.component_id
                        ),
                    )
                )

        # we are going to be uing this in the UI soon
        if not self.category or self.category.value == "unknown":
            problems.append(
                Claim(
                    kind="no-category",
                    icon="warning",
                    summary="Firmware category has not been set",
                    description="All components should have a defined update category "
                    "before being moved to stable.\n"
                    "This also can be set in the .metainfo.xml file.",
                    url=url_for(
                        "components.route_show", component_id=self.component_id
                    ),
                )
            )

        # firmware can't be pushed to public with a private protocol
        if self.protocol and not self.protocol.is_public:
            problems.append(
                Claim(
                    kind="no-protocol",
                    icon="warning",
                    summary="Update protocol is not public",
                    url=url_for(
                        "components.route_show", component_id=self.component_id
                    ),
                )
            )

        # some firmware requires a source URL
        if self.requires_source_url and not self.source_url:
            problems.append(
                Claim(
                    kind="no-source",
                    icon="warning",
                    summary="Update does not link to source code",
                    description="Firmware that uses the GNU General Public License has to "
                    "provide a link to the source code used to build the firmware.",
                    url=url_for(
                        "components.route_show",
                        component_id=self.component_id,
                        page="update",
                    ),
                )
            )

        # the URL has to be valid if provided
        if self.details_url and not _is_valid_url(self.details_url):
            problems.append(
                Claim(
                    kind="invalid-details-url",
                    icon="warning",
                    summary="The update details URL was provided but not valid",
                    url=url_for(
                        "components.route_show",
                        page="update",
                        component_id=self.component_id,
                    ),
                )
            )
        if self.source_url and not _is_valid_url(self.source_url):
            problems.append(
                Claim(
                    kind="invalid-source-url",
                    icon="warning",
                    summary="The release source URL was provided but not valid",
                    url=url_for(
                        "components.route_show",
                        page="update",
                        component_id=self.component_id,
                    ),
                )
            )

        # the OEM doesn't manage this namespace
        values = [ns.value for ns in self.fw.vendor.namespaces]
        if not values:
            problems.append(
                Claim(
                    kind="no-vendor-namespace",
                    icon="warning",
                    summary="No AppStream namespace for vendor",
                    description="Your vendor does not have permission to own this AppStream ID "
                    "component prefix.\n"
                    "Please either change the firmware vendor or contact the "
                    "LVFS administrator to fix this.",
                )
            )
        elif self.appstream_id_prefix not in values:
            problems.append(
                Claim(
                    kind="invalid-vendor-namespace",
                    icon="warning",
                    summary="Invalid vendor namespace",
                    description="{} does not have permission to own the AppStream ID "
                    "component prefix of {}.\n"
                    "Please either change the vendor to the correct OEM or contact "
                    "the LVFS administrator to fix this.".format(
                        self.fw.vendor_odm.display_name, self.appstream_id_prefix
                    ),
                    url=url_for(
                        "firmware.route_affiliation", firmware_id=self.fw.firmware_id
                    ),
                )
            )

        # name_variant_suffix contains a word in the name
        if self.name_variant_suffix:
            nvs_words = self.name_variant_suffix.split(" ")
            nvs_kws = [_sanitize_keyword(word) for word in nvs_words]
            for word in self.name.split(" "):
                if _sanitize_keyword(word) in nvs_kws:
                    problems.append(
                        Claim(
                            kind="invalid-name-variant-suffix",
                            icon="warning",
                            summary="{} is already part of the <name>".format(word),
                            url=url_for(
                                "components.route_show", component_id=self.component_id
                            ),
                        )
                    )

        # name contains a banned word
        if self.name:
            name = self.name.lower()
            for word in ["bios", "firmware", "update"]:
                if name.find(word) != -1:
                    problems.append(
                        Claim(
                            kind="invalid-name",
                            icon="warning",
                            summary="{} is is banned as part of <name>".format(word),
                            url=url_for(
                                "components.route_show", component_id=self.component_id
                            ),
                        )
                    )

        # name contains the vendor
        if self.name and self.fw.vendor.display_name:
            if self.name.upper().find(self.fw.vendor.display_name.upper()) != -1:
                problems.append(
                    Claim(
                        kind="invalid-name",
                        icon="warning",
                        summary="The vendor should not be part of the name",
                        description="The vendor name {} should not be be included in {}.\n"
                        "Please remove the vendor name from the "
                        "firmware name as it will be prefixed "
                        "automatically as required.".format(
                            self.fw.vendor.display_name, self.name
                        ),
                        url=url_for(
                            "components.route_show", component_id=self.component_id
                        ),
                    )
                )

        # only very new fwupd versions support <branch>
        if self.branch:
            req = self.find_req("id", "org.freedesktop.fwupd")
            if (
                not req
                or req.compare != "ge"
                or StrictVersion(req.version) < StrictVersion("1.5.0")
            ):
                problems.append(
                    Claim(
                        kind="requirement-missing",
                        icon="warning",
                        summary="A requirement is missing for branch",
                        description="The requirement of org.freedesktop.fwupd "
                        ">= 1.5.0 is missing to allow setting "
                        "a branch name",
                        url=url_for(
                            "components.route_show", component_id=self.component_id
                        ),
                    )
                )

        # the vendor has to have been permitted to use this branch
        if self.branch:
            branches = [br.value for br in self.fw.vendor.branches]
            if not branches:
                problems.append(
                    Claim(
                        kind="branch-invalid",
                        icon="warning",
                        summary="The specified component branch was invalid",
                        description="This vendor cannot ship firmware with branches",
                        url=url_for(
                            "components.route_show", component_id=self.component_id
                        ),
                    )
                )
            elif self.branch not in branches:
                problems.append(
                    Claim(
                        kind="branch-invalid",
                        icon="warning",
                        summary="The specified component branch was invalid",
                        description="This vendor is only allowed to use branches {}".format(
                            "|".join(branches)
                        ),
                        url=url_for(
                            "components.route_show", component_id=self.component_id
                        ),
                    )
                )

        # release tag is not provided and required or user has used the example
        if self.category:
            tag = self.vendor_tag
            if tag:
                if tag.enforce and not self.release_tag:
                    problems.append(
                        Claim(
                            kind="release-id-invalid",
                            icon="warning",
                            summary="The component requries a {}".format(
                                tag.name
                            ),
                            description="All components for vendor {} with category {} "
                            "must have a release {}.".format(
                                self.fw.vendor.display_name_with_team,
                                self.category.name,
                                tag.name,
                            ),
                            url=url_for(
                                "components.route_show", component_id=self.component_id
                            ),
                        )
                    )
                if tag.example == self.release_tag:
                    problems.append(
                        Claim(
                            kind="release-id-invalid",
                            icon="warning",
                            summary="The component requries a valid release {}".format(
                                tag.name
                            ),
                            description="All components for vendor {} with category {} "
                            "must have the correct release {}.".format(
                                self.fw.vendor.display_name_with_team,
                                self.category.name,
                                tag.name,
                            ),
                            url=url_for(
                                "components.route_show", component_id=self.component_id
                            ),
                        )
                    )

        # add all CVE problems
        for issue in self.issues:
            if issue.problem:
                problems.append(issue.problem)

        # set the URL for the component
        for problem in problems:
            if problem.url:
                continue
            problem.url = url_for(
                "components.route_show", component_id=self.component_id, page="update"
            )
        return problems

    @property
    def has_complex_requirements(self) -> bool:
        seen: List[str] = []
        for rq in self.requirements:
            if rq.kind == "firmware":
                if rq.value not in [None, "bootloader"]:
                    return True
                if rq.depth:
                    return True
            key = rq.kind + ":" + str(rq.value)
            if key in seen:
                return True
            seen.append(key)
        return False

    def add_keywords_from_string(self, value: str, priority: int = 0) -> None:
        existing_keywords: Dict[str, ComponentKeyword] = {}
        for kw in self.keywords:
            existing_keywords[kw.value] = kw
        for keyword in _split_search_string(value):
            if keyword in existing_keywords:
                continue
            self.keywords.append(ComponentKeyword(value=keyword, priority=priority))

    def find_req(self, kind: str, value: str) -> Optional["ComponentRequirement"]:
        """ Find a ComponentRequirement from the kind and/or value """
        for rq in self.requirements:
            if rq.kind != kind:
                continue
            if rq.value != value:
                continue
            return rq
        return None

    def add_claim(self, claim: Claim):
        for component_claim in self.component_claims:
            if component_claim.claim.kind == claim.kind:
                return
        self.component_claims.append(ComponentClaim(claim=claim))

    def check_acl(self, action: str, user: Optional[User] = None) -> bool:

        # fall back
        if not user:
            user = g.user
        if not user:
            return False
        if user.check_acl("@admin"):
            return True

        # depends on the action requested
        if action in (
            "@modify-keywords",
            "@modify-requirements",
            "@modify-checksums",
            "@modify-appstream-id",
            "@modify-updateinfo",
        ):
            if not self.fw.remote.is_public:
                if user.check_acl("@qa") and self.fw._is_permitted_action(action, user):
                    return True
                if self.fw._is_owner(user):
                    return True
            return False
        raise NotImplementedError(
            "unknown security check action: %s:%s" % (self, action)
        )

    def __repr__(self) -> str:
        return "Component object %s" % self.appstream_id


class ComponentRequirement(db.Model):

    __tablename__ = "requirements"

    requirement_id = Column(Integer, primary_key=True)
    component_id = Column(
        Integer, ForeignKey("components.component_id"), nullable=False, index=True
    )
    kind = Column(Text, nullable=False)
    value = Column(Text, default=None)
    compare = Column(Text, default=None)
    version = Column(Text, default=None)
    depth = Column(Integer, default=None)

    md = relationship("Component", back_populates="requirements")

    def __repr__(self) -> str:
        return "ComponentRequirement object %s/%s/%s/%s" % (
            self.kind,
            self.value,
            self.compare,
            self.version,
        )


class ComponentGuid(db.Model):

    __tablename__ = "guids"
    guid_id = Column(Integer, primary_key=True)
    component_id = Column(
        Integer, ForeignKey("components.component_id"), nullable=False, index=True
    )
    value = Column(Text, nullable=False)

    md = relationship("Component", back_populates="guids")

    def __repr__(self) -> str:
        return "ComponentGuid object %s" % self.guid_id


class ComponentKeyword(db.Model):

    __tablename__ = "keywords"

    keyword_id = Column(Integer, primary_key=True)
    component_id = Column(
        Integer, ForeignKey("components.component_id"), nullable=False, index=True
    )
    priority = Column(Integer, default=0)
    value = Column(Text, nullable=False)

    md = relationship("Component", back_populates="keywords")

    def __repr__(self) -> str:
        return "ComponentKeyword object %s" % self.value


class ComponentChecksum(db.Model):

    __tablename__ = "checksums"

    checksum_id = Column(Integer, primary_key=True)
    component_id = Column(
        Integer, ForeignKey("components.component_id"), nullable=False, index=True
    )
    kind = Column(Text, nullable=False, default=None)
    value = Column(Text, nullable=False, default=None)

    md = relationship("Component")

    def __repr__(self) -> str:
        return "ComponentChecksum object %s(%s)" % (self.kind, self.value)
