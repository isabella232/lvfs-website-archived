#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2017-2018 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+

import datetime
from typing import Dict, List

from flask import Blueprint, render_template, flash, redirect, url_for, g, make_response
from flask_login import login_required

from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound

from lvfs import db

from lvfs.util import admin_login_required
from lvfs.categories.models import Category
from lvfs.firmware.models import Firmware
from lvfs.components.models import Component, ComponentGuid, ComponentShard
from lvfs.vendors.models import Vendor
from lvfs.metadata.models import Remote

bp_devices = Blueprint('devices', __name__, template_folder='templates')


@bp_devices.route('/status')
@bp_devices.route('/status/<int:vendor_id>')
@bp_devices.route('/status/<int:vendor_id>/<int:category_id>')
@login_required
def route_status(vendor_id = None, category_id = None):

    # fall back to the current vendor
    if not vendor_id:
        vendor = g.user.vendor
    else:
        try:
            vendor = db.session.query(Vendor).filter(Vendor.vendor_id == vendor_id).one()
        except NoResultFound as _:
            flash('No vendor with ID {} exists'.format(vendor_id), 'danger')
            return redirect(url_for('devices.route_status'))

    # find all the components uploaded by the vendor
    appstream_ids: Dict[str, Dict[str, Component]] = {}
    md_by_id: Dict[str, Component] = {}
    cats_by_id: Dict[int, Category] = {}
    for md in db.session.query(Component)\
                        .join(Firmware)\
                        .filter((Firmware.vendor_id == vendor.vendor_id) | \
                                (Firmware.vendor_odm_id == vendor.vendor_id))\
                        .join(Remote).filter(Remote.name != 'deleted'):

        # permission check
        if not md.fw.check_acl('@view'):
            continue

        # build available categories
        if md.category_id:
            cats_by_id[md.category_id] = md.category

        # filter
        if category_id:
            if category_id != md.category_id:
                continue

        # put something human readable in the UI
        md_by_id[md.appstream_id] = md

        # appstream ID not yet added
        md_by_remote = appstream_ids.get(md.appstream_id)
        if not md_by_remote:
            appstream_ids[md.appstream_id] = { md.fw.remote.key: md }
            continue

        # remote not yet added
        old_md = md_by_remote.get(md.fw.remote.key)
        if not old_md:
            md_by_remote[md.fw.remote.key] = md
            continue

        # replace with newer version
        if md > old_md:
            md_by_remote[md.fw.remote.key] = md

    return render_template('device-status.html',
                           category='firmware',
                           cats=cats_by_id.values(),
                           vendor=vendor,
                           category_id=category_id,
                           appstream_ids=appstream_ids,
                           md_by_id=md_by_id)


@bp_devices.route('/status/csv')
@bp_devices.route('/status/csv/<int:vendor_id>')
@bp_devices.route('/status/csv/<int:vendor_id>/<int:category_id>')
@login_required
def route_status_csv(vendor_id=None, category_id=None):

    # fall back to the current vendor
    if not vendor_id:
        vendor = g.user.vendor
    else:
        try:
            vendor = db.session.query(Vendor).filter(Vendor.vendor_id == vendor_id).one()
        except NoResultFound as _:
            flash('No vendor with ID {} exists'.format(vendor_id), 'danger')
            return redirect(url_for('devices.route_status'))

    # find all the components uploaded by the vendor
    appstream_ids: Dict[str, Dict[str, Component]] = {}
    md_by_id: Dict[str, Component] = {}
    for md in db.session.query(Component)\
                        .join(Firmware)\
                        .filter((Firmware.vendor_id == vendor.vendor_id) | \
                                (Firmware.vendor_odm_id == vendor.vendor_id))\
                        .join(Remote).filter(Remote.name != 'deleted'):

        # permission check
        if not md.fw.check_acl('@view'):
            continue

        # filter
        if category_id:
            if category_id != md.category_id:
                continue

        # put something human readable in the UI
        md_by_id[md.appstream_id] = md

        # appstream ID not yet added
        md_by_remote = appstream_ids.get(md.appstream_id)
        if not md_by_remote:
            appstream_ids[md.appstream_id] = {md.fw.remote.key: md}
            continue

        # remote not yet added
        old_md = md_by_remote.get(md.fw.remote.key)
        if not old_md:
            md_by_remote[md.fw.remote.key] = md
            continue

        # replace with newer version
        if md > old_md:
            md_by_remote[md.fw.remote.key] = md

    # header
    csv: List[str] = []
    remote_names: List[str] = ['private', 'embargo', 'testing', 'stable']
    csv.append(','.join(['appstream_id', 'model'] + remote_names + ['vendor_odm', 'user']))
    for appstream_id in sorted(appstream_ids):
        md_by_remote = appstream_ids[appstream_id]
        csv_line: List[str] = []
        csv_line.append(appstream_id)
        csv_line.append('"{}"'.format(md_by_id[appstream_id].name_with_vendor))
        md_best = None
        for remote_id in remote_names:
            md = md_by_remote.get(remote_id)
            if md:
                md_best = md
            csv_line.append(md.version_display if md else '')
        if md_best:
            csv_line.append(md_best.fw.vendor_odm.group_id)
            csv_line.append(md_best.fw.user.username)
        else:
            csv_line.append('')
            csv_line.append('')
        csv.append(','.join(csv_line))

    response = make_response('\n'.join(csv))
    response.headers.set('Content-Type', 'text/csv')
    response.headers.set('Content-Disposition', 'attachment', filename='device-status.csv')
    return response


@bp_devices.route('/admin')
@login_required
@admin_login_required
def route_list_admin():
    """
    Show all devices -- probably only useful for the admin user.
    """

    # get all the appstream_ids we can target
    devices: List[str] = []
    seen_appstream_id: Dict[str, bool] = {}
    for fw in db.session.query(Firmware):
        for md in fw.mds:
            if md.appstream_id in seen_appstream_id:
                continue
            seen_appstream_id[md.appstream_id] = True
            devices.append(md.appstream_id)

    return render_template('devices.html', devices=devices)

def _dt_from_quarter(year: int, quarter: int):
    month = (quarter * 3) + 1
    if month > 12:
        month %= 12
        year += 1
    return datetime.datetime(year, month, 1)

def _get_fws_for_appstream_id(value):

    # old, deprecated GUID view
    if len(value.split('-')) == 5:
        return db.session.query(Firmware).\
                    join(Remote).filter(Remote.is_public).\
                    join(Component).join(ComponentGuid).filter(ComponentGuid.value == value).\
                    order_by(Firmware.timestamp.desc()).all()

    # new, AppStream ID view
    return db.session.query(Firmware).\
                    join(Remote).filter(Remote.is_public).\
                    join(Component).filter(Component.appstream_id == value).\
                    order_by(Firmware.timestamp.desc()).all()

@bp_devices.route('/<appstream_id>')
def route_show(appstream_id):
    """
    Show information for one device, which can be seen without a valid login
    """
    fws = _get_fws_for_appstream_id(appstream_id)

    # work out the previous version for the shard diff
    fw_old = None
    fw_previous: Dict[Firmware, Firmware] = {}
    for fw in fws:
        if fw_old:
            fw_previous[fw_old] = fw
        fw_old = fw

    return render_template('device.html',
                           appstream_id=appstream_id,
                           fws=fws,
                           fw_previous=fw_previous)

@bp_devices.route('/<appstream_id>/atom')
def route_show_atom(appstream_id):
    """
    Show information for one device, which can be seen without a valid login
    """
    fws = _get_fws_for_appstream_id(appstream_id)
    return render_template('device-atom.xml',
                           appstream_id=appstream_id,
                           fws=fws)

@bp_devices.route('/component/<int:component_id>')
def route_shards(component_id):
    """
    Show information for one firmware, which can be seen without a valid login
    """
    md = db.session.query(Component).filter(Component.component_id == component_id).first()
    if not md:
        flash('No component with ID {} exists'.format(component_id), 'danger')
        return redirect(url_for('devices.route_show', appstream_id=md.appstream_id))
    return render_template('device-shards.html', md=md, appstream_id=md.appstream_id)

@bp_devices.route('/component/<int:component_id_old>/<int:component_id_new>')
def route_shards_diff(component_id_old, component_id_new):
    """
    Show information for one firmware, which can be seen without a valid login
    """
    md_old = db.session.query(Component).filter(Component.component_id == component_id_old).first()
    if not md_old:
        flash('No component with ID {} exists'.format(component_id_old), 'danger')
        return redirect(url_for('devices.route_list_admin'))
    md_new = db.session.query(Component).filter(Component.component_id == component_id_new).first()
    if not md_new:
        flash('No component with ID {} exists'.format(component_id_new), 'danger')
        return redirect(url_for('devices.route_list_admin'))

    # shards added
    shard_guids: Dict[str, ComponentShard] = {}
    for shard in md_old.shards:
        shard_guids[shard.guid] = shard
    shards_added: List[ComponentShard] = []
    for shard in md_new.shards:
        if shard.guid not in shard_guids:
            shards_added.append(shard)

    # shards removed
    shard_guids: Dict[str, ComponentShard] = {}
    for shard in md_new.shards:
        shard_guids[shard.guid] = shard
    shards_removed: List[ComponentShard] = []
    for shard in md_old.shards:
        if shard.guid not in shard_guids:
            shards_removed.append(shard)

    # shards changed
    shard_checksums: Dict[str, ComponentShard] = {}
    for shard in md_new.shards:
        shard_checksums[shard.checksum] = shard
    shards_changed: List[ComponentShard] = []
    for shard in md_old.shards:
        if shard.guid in shard_guids:
            shard_old = shard_guids[shard.guid]
            if shard.checksum not in shard_checksums:
                shards_changed.append((shard_old, shard))

    return render_template('device-shards-diff.html',
                           md_old=md_old, md_new=md_new,
                           shards_added=shards_added,
                           shards_removed=shards_removed,
                           shards_changed=shards_changed,
                           appstream_id=md_old.appstream_id)

@bp_devices.route('/<appstream_id>/analytics')
def route_analytics(appstream_id):
    """
    Show analytics for one device, which can be seen without a valid login
    """
    data: List[int] = []
    labels: List[str] = []
    now = datetime.date.today()
    fws = _get_fws_for_appstream_id(appstream_id)
    if not fws:
        flash('No firmware with that AppStream ID or GUID exists', 'danger')
        return redirect(url_for('devices.route_list_admin'))
    for i in range(-2, 1):
        year = now.year + i
        for quarter in range(0, 4):
            t1 = _dt_from_quarter(year, quarter)
            t2 = _dt_from_quarter(year, quarter + 1)
            cnt = 0
            for fw in fws:
                if fw.timestamp.replace(tzinfo=None) >= t1 and fw.timestamp.replace(tzinfo=None) < t2:
                    cnt += 1
            labels.append("%04iQ%i" % (year, quarter + 1))
            data.append(cnt)

    return render_template('device-analytics.html',
                           appstream_id=appstream_id,
                           labels=labels,
                           data=data,
                           fws=fws)

@bp_devices.route('/')
def route_list():

    # get a list of firmwares with a map of components
    fws = db.session.query(Firmware).\
                           join(Remote).filter(Remote.is_public).\
                           join(Component).distinct(Component.appstream_id).\
                           order_by(Component.appstream_id, Firmware.timestamp.desc()).\
                           all()
    vendors: List[Vendor] = []
    mds_by_vendor: Dict[Vendor, List[Component]] = {}
    for fw in fws:
        vendor = fw.vendor
        if vendor not in vendors:
            vendors.append(vendor)
        if not vendor in mds_by_vendor:
            mds_by_vendor[vendor] = []
        mds_by_vendor[vendor].append(fw.md_prio)

    # ensure list is sorted
    for vendor in mds_by_vendor:
        mds_by_vendor[vendor].sort(key=lambda obj: obj.name)

    return render_template('devicelist.html',
                           vendors=sorted(vendors),
                           mds_by_vendor=mds_by_vendor)


@bp_devices.route('/new')
def route_new():

    # get most recent supported devices
    stmt = db.session.query(Component.appstream_id).\
                            group_by(Component.appstream_id).\
                            having(func.count() == 1).\
                            subquery()
    fws_recent = db.session.query(Firmware).\
                                  join(Remote).filter(Remote.is_public).\
                                  join(Component).\
                                  join(stmt, Component.appstream_id == stmt.c.appstream_id).\
                                  order_by(Firmware.timestamp.desc()).\
                                  limit(30).all()

    return render_template('device-new.html',
                           devices=fws_recent)
