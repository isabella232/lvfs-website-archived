#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+

import gzip
import csv
from typing import Dict
from collections import defaultdict
from io import StringIO

import requests

from lvfs import app, db, tq

from lvfs.util import _event_log

from .models import Geoip


def _convert_ip_addr_to_integer(ip_addr: str) -> int:
    try:
        ip_vals = ip_addr.split(".")
        return (
            int(ip_vals[0]) * 0x1000000
            + int(ip_vals[1]) * 0x10000
            + int(ip_vals[2]) * 0x100
            + int(ip_vals[3])
        )
    except (IndexError, ValueError) as _:
        return 0x0


def _geoip_import_data(data: str) -> None:

    # find the last added Geoip ID
    try:
        (last_id,) = (
            db.session.query(Geoip.geoip_id).order_by(Geoip.geoip_id.desc()).first()
        )
    except TypeError as _:
        last_id = 0

    # import the new data
    try:
        reader = csv.reader(StringIO(data))
    except ValueError as e:
        raise NotImplementedError("No CSV object could be decoded") from e
    countries: Dict[str, int] = defaultdict(int)
    for row in reader:
        try:
            if row[0].startswith("#"):
                continue
            geo = Geoip(
                addr_start=int(row[0]), addr_end=int(row[1]), country_code=row[4]
            )
            countries[row[4]] += 1
            db.session.add(geo)
        except (IndexError, ValueError) as _:
            pass

    # commit new IDs
    db.session.commit()

    # remove old IDs
    for geo in db.session.query(Geoip).filter(Geoip.geoip_id <= last_id):
        db.session.delete(geo)
    db.session.commit()

    # log
    _event_log("Imported GeoIP data: {}".format(str(countries)))


def _geoip_import_url() -> None:

    # download URL
    session = requests.Session()
    rv = session.get(app.config["GEOIP_URL"])
    if rv.status_code != 200:
        raise NotImplementedError("failed to upload to {}: {}".format(rv.url, rv.text))

    # parse CSV Gzipped data
    try:
        payload = gzip.decompress(rv.content)
    except (OSError, UnicodeDecodeError) as e:
        raise NotImplementedError("no GZipped object could be decoded") from e

    # import data
    _geoip_import_data(payload.decode(errors="ignore"))


@tq.task(max_retries=3, default_retry_delay=5, task_time_limit=6000)
def _async_geoip_import_url() -> None:
    _geoip_import_url()
