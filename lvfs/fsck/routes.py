#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+

from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required

from lvfs import db

from lvfs.util import admin_login_required, _error_internal
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
