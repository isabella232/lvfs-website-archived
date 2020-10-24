#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+

from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required

from celery.schedules import crontab

from lvfs.util import admin_login_required

from lvfs import db, tq

from .models import Geoip
from .utils import (
    _async_geoip_import_url,
    _convert_ip_addr_to_integer,
)

bp_geoip = Blueprint("geoip", __name__, template_folder="templates")


@tq.on_after_finalize.connect
def setup_periodic_tasks(sender, **_):
    sender.add_periodic_task(
        crontab(day=1, hour=1, minute=34), _async_geoip_import_url.s(),
    )


@bp_geoip.route("/")
@login_required
@admin_login_required
def route_view():
    return render_template("geoip.html", category="admin")


@bp_geoip.route("/import/data", methods=["POST"])
@login_required
@admin_login_required
def route_import_data():

    try:
        geo = Geoip(
            addr_start=int(request.form["addr_start"]),
            addr_end=int(request.form["addr_end"]),
            country_code=request.form["country_code"],
        )
    except IndexError as e:
        flash("Invalid request: " + str(e), "warning")
        return redirect(url_for("geoip.route_view"))
    db.session.add(geo)
    db.session.commit()

    flash("Added GeoIP data", "info")
    return redirect(url_for("geoip.route_view"))


@bp_geoip.route("/import", methods=["POST"])
@login_required
@admin_login_required
def route_import():

    # asynchronously rebuilt
    flash("Updating GeoIP data", "info")
    _async_geoip_import_url.apply_async(queue="metadata")

    return redirect(url_for("geoip.route_view"))


@bp_geoip.route("/check", methods=["POST"])
@login_required
def route_check():

    try:
        ip_addr = request.form["ip_addr"]
        ip_val = _convert_ip_addr_to_integer(ip_addr)
    except IndexError as e:
        flash("Cannot parse IP address: " + str(e), "warning")
        return redirect(url_for("geoip.route_view"))
    if not ip_val:
        flash("Cannot parse IP address: {}".format(ip_addr), "warning")
        return redirect(url_for("geoip.route_view"))
    try:
        (country_code,) = (
            db.session.query(Geoip.country_code)
            .filter(Geoip.addr_start < ip_val)
            .filter(Geoip.addr_end > ip_val)
            .first()
        )
    except TypeError as e:
        flash("Cannot find IP range: {}".format(ip_addr), "warning")
        return redirect(url_for("geoip.route_view"))

    flash("Country code: {}".format(country_code), "info")
    return redirect(url_for("geoip.route_view"))
