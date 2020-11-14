#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+

from flask import Blueprint, request, url_for, redirect, flash, render_template
from flask_login import login_required

from lvfs import db

from lvfs.util import admin_login_required
from lvfs.util import _error_internal

from .models import License

bp_licenses = Blueprint("licenses", __name__, template_folder="templates")


@bp_licenses.route("/")
@login_required
@admin_login_required
def route_list():
    licenses = db.session.query(License).order_by(License.value.asc()).all()
    return render_template("license-list.html", category="admin", licenses=licenses)


@bp_licenses.route("/create", methods=["POST"])
@login_required
@admin_login_required
def route_create():
    # ensure has enough data
    if "value" not in request.form:
        return _error_internal("No form data found!")
    value = request.form["value"]
    if not value or value.find(" ") != -1:
        flash("Failed to add license: Value is not valid", "warning")
        return redirect(url_for("licenses.route_list"))

    # already exists
    if db.session.query(License).filter(License.value == value).first():
        flash("Failed to add license: The license already exists", "info")
        return redirect(url_for("licenses.route_list"))

    # add license
    lic = License(value=request.form["value"])
    db.session.add(lic)
    db.session.commit()
    flash("Added license", "info")
    return redirect(url_for("licenses.route_show", license_id=lic.license_id))


@bp_licenses.route("/<int:license_id>/delete", methods=["POST"])
@login_required
@admin_login_required
def route_delete(license_id):

    # get license
    lic = db.session.query(License).filter(License.license_id == license_id).first()
    if not lic:
        flash("No license found", "info")
        return redirect(url_for("licenses.route_list"))

    # delete
    db.session.delete(lic)
    db.session.commit()
    flash("Deleted license", "info")
    return redirect(url_for("licenses.route_list"))


@bp_licenses.route("/<int:license_id>/modify", methods=["POST"])
@login_required
@admin_login_required
def route_modify(license_id):

    # find license
    lic = db.session.query(License).filter(License.license_id == license_id).first()
    if not lic:
        flash("No license found", "info")
        return redirect(url_for("licenses.route_list"))

    # modify license
    lic.is_content = bool("is_content" in request.form)
    lic.is_approved = bool("is_approved" in request.form)
    lic.requires_source = bool("requires_source" in request.form)
    for key in ["name", "text"]:
        if key in request.form:
            setattr(lic, key, request.form[key] or None)
    db.session.commit()

    # success
    flash("Modified license", "info")
    return redirect(url_for("licenses.route_show", license_id=license_id))


@bp_licenses.route("/<int:license_id>")
@login_required
@admin_login_required
def route_show(license_id):

    # find license
    lic = db.session.query(License).filter(License.license_id == license_id).first()
    if not lic:
        flash("No license found", "info")
        return redirect(url_for("licenses.route_list"))

    # show details
    return render_template("license-details.html", category="admin", lic=lic)
