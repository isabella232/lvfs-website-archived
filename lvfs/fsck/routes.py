#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+

from collections import defaultdict
from typing import Dict

from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required

from lvfs import db

from lvfs.util import admin_login_required, _error_internal
from lvfs.components.models import Component
from lvfs.licenses.models import License
from lvfs.users.models import User
from lvfs.analytics.utils import _async_generate_stats

from .utils import _async_fsck_update_descriptions

bp_fsck = Blueprint("fsck", __name__, template_folder="templates")


@bp_fsck.route("/")
@login_required
@admin_login_required
def route_view():
    return render_template("fsck.html", category="admin")


@bp_fsck.route("/update_descriptions", methods=["POST"])
@login_required
@admin_login_required
def route_update_descriptions():

    for key in ["search", "replace"]:
        if key not in request.form or not request.form[key]:
            return _error_internal("No %s specified!" % key)

    # asynchronously rebuilt
    flash("Updating update descriptions", "info")
    _async_fsck_update_descriptions.apply_async(
        args=(request.form["search"], request.form["replace"],), queue="metadata"
    )

    return redirect(url_for("fsck.route_view"))


@bp_fsck.route("/generate_stats", methods=["POST"])
@login_required
@admin_login_required
def route_generate_stats():

    # asynchronously rebuilt
    flash("Generating stats for yesterday", "info")
    _async_generate_stats.apply_async()
    return redirect(url_for("fsck.route_view"))


@bp_fsck.route("/lockdown", methods=["POST"])
@login_required
@admin_login_required
def route_lockdown():

    # this is unrecoverable
    for user in db.session.query(User).filter(User.user_id != 1):
        user.auth_type = "disabled"
    db.session.commit()
    flash("Disabled all users", "warning")

    return redirect(url_for("fsck.route_view"))


@bp_fsck.route("/project_license", methods=["POST"])
@login_required
@admin_login_required
def route_project_license():

    # create map of all licenses
    license_map: Dict[str, License] = {}
    for lic in db.session.query(License):
        license_map[lic.value] = lic
    lic = license_map.get("LicenseRef-proprietary")
    if lic:
        license_map["proprietary"] = lic
        license_map["Proprietary"] = lic

    cnt = 0
    unknown_licenses: Dict[str, int] = defaultdict(int)
    for component_id in db.session.query(Component.component_id):

        md = (
            db.session.query(Component)
            .filter(Component.component_id == component_id)
            .first()
        )

        # fixup project license
        if not md.project_license and md.unused_project_license:
            md.project_license = license_map.get(md.unused_project_license)
            if md.project_license:
                cnt += 1
                # md.unused_project_license = None
            else:
                unknown_licenses[md.unused_project_license] += 1

        # fixup metadata license
        if not md.metadata_license and md.unused_metadata_license:
            md.metadata_license = license_map.get(md.unused_metadata_license)
            # some early Lenovo ThinkPad firmware (before we were validating the
            # correct values on upload); cleared with Lenovo Legal.
            if (
                md.metadata_license
                and md.metadata_license.value == "LicenseRef-proprietary"
            ):
                md.metadata_license = license_map.get("CC0-1.0")
            if md.metadata_license:
                cnt += 1
                # md.unused_metadata_license
            else:
                unknown_licenses[md.metadata_license] += 1

    db.session.commit()

    # success
    if cnt:
        flash("Fixed {} license values".format(cnt), "info")
    else:
        flash("No license values to fix", "info")
    if unknown_licenses:
        tmp = ','.join(unknown_licenses.keys())
        flash("Unknown license values {}".format(tmp), "warning")
    else:
        flash("No unknown license values", "info")
    return redirect(url_for("fsck.route_view"))
