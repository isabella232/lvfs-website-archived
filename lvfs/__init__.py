#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=wrong-import-position,wrong-import-order

import os
import socket
import sqlalchemy
import logging

from logging.handlers import SMTPHandler

from flask import Blueprint, Flask, flash, render_template, message_flashed, request, redirect, url_for, Response, g
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from flask_oauthlib.client import OAuth
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.local import LocalProxy
import posixpath

from lvfs.celery import FlaskCelery
from lvfs.dbutils import drop_db, init_db, anonymize_db

app: Flask = Flask(__name__)
app_config_fn = os.environ.get('LVFS_APP_SETTINGS', 'custom.cfg')
if os.path.exists(os.path.join('lvfs', app_config_fn)):
    app.config.from_pyfile(app_config_fn)
else:
    app.config.from_pyfile('flaskapp.cfg')
if 'LVFS_CUSTOM_SETTINGS' in os.environ:
    app.config.from_envvar('LVFS_CUSTOM_SETTINGS')

def cdn_url_builder(_error, endpoint, values):
    if endpoint != 'cdn':
        return None
    return posixpath.join(app.config['CDN_DOMAIN'], 'static', values['filename'])

app.url_build_error_handlers.append(cdn_url_builder)

oauth: OAuth = OAuth(app)

db: SQLAlchemy = SQLAlchemy(app)

mail: Mail = Mail(app)

csrf: CSRFProtect = CSRFProtect(app)

migrate: Migrate = Migrate(app, db)

lm: LoginManager = LoginManager(app)
lm.login_view = 'login1'

from lvfs.pluginloader import Pluginloader
ploader = Pluginloader('plugins')

tq: FlaskCelery = FlaskCelery(app.name, broker=app.config['CELERY_BROKER_URL'])
tq.init_app(app)

from lvfs.agreements.routes import bp_agreements
from lvfs.analytics.routes import bp_analytics
from lvfs.categories.routes import bp_categories
from lvfs.licenses.routes import bp_licenses
from lvfs.claims.routes import bp_claims
from lvfs.components.routes import bp_components
from lvfs.devices.routes import bp_devices
from lvfs.hsireports.routes import bp_hsireports
from lvfs.mdsync.routes import bp_mdsync
from lvfs.docs.routes import bp_docs
from lvfs.firmware.routes import bp_firmware
from lvfs.issues.routes import bp_issues
from lvfs.main.routes import bp_main
from lvfs.metadata.routes import bp_metadata
from lvfs.fsck.routes import bp_fsck
from lvfs.geoip.routes import bp_geoip
from lvfs.protocols.routes import bp_protocols
from lvfs.queries.routes import bp_queries
from lvfs.reports.routes import bp_reports
from lvfs.search.routes import bp_search
from lvfs.settings.routes import bp_settings
from lvfs.shards.routes import bp_shards
from lvfs.telemetry.routes import bp_telemetry
from lvfs.tests.routes import bp_tests
from lvfs.upload.routes import bp_upload
from lvfs.users.routes import bp_users
from lvfs.vendors.routes import bp_vendors
from lvfs.verfmts.routes import bp_verfmts

app.register_blueprint(bp_agreements, url_prefix='/lvfs/agreements')
app.register_blueprint(bp_analytics, url_prefix='/lvfs/analytics')
app.register_blueprint(bp_categories, url_prefix='/lvfs/categories')
app.register_blueprint(bp_licenses, url_prefix='/lvfs/licenses')
app.register_blueprint(bp_claims, url_prefix='/lvfs/claims')
app.register_blueprint(bp_components, url_prefix='/lvfs/components')
app.register_blueprint(bp_devices, url_prefix='/lvfs/devices')
app.register_blueprint(bp_mdsync, url_prefix='/lvfs/mdsync')
app.register_blueprint(bp_docs, url_prefix='/lvfs/docs')
app.register_blueprint(bp_firmware, url_prefix='/lvfs/firmware')
app.register_blueprint(bp_issues, url_prefix='/lvfs/issues')
app.register_blueprint(bp_main)
app.register_blueprint(bp_metadata, url_prefix='/lvfs/metadata')
app.register_blueprint(bp_fsck, url_prefix='/lvfs/fsck')
app.register_blueprint(bp_geoip, url_prefix='/lvfs/geoip')
app.register_blueprint(bp_protocols, url_prefix='/lvfs/protocols')
app.register_blueprint(bp_queries, url_prefix='/lvfs/queries')
app.register_blueprint(bp_reports, url_prefix='/lvfs/reports')
app.register_blueprint(bp_search, url_prefix='/lvfs/search')
app.register_blueprint(bp_settings, url_prefix='/lvfs/settings')
app.register_blueprint(bp_shards, url_prefix='/lvfs/shards')
app.register_blueprint(bp_telemetry, url_prefix='/lvfs/telemetry')
app.register_blueprint(bp_tests, url_prefix='/lvfs/tests')
app.register_blueprint(bp_upload, url_prefix='/lvfs/upload')
app.register_blueprint(bp_users, url_prefix='/lvfs/users')
app.register_blueprint(bp_vendors, url_prefix='/lvfs/vendors')
app.register_blueprint(bp_verfmts, url_prefix='/lvfs/verfmts')
app.register_blueprint(bp_hsireports, url_prefix='/lvfs/hsireports')

@app.before_request
def before_request_func():
    g.container_id = socket.gethostname()

@app.cli.command('initdb')
def initdb_command():
    init_db(db)

@app.cli.command('dropdb')
def dropdb_command():
    drop_db(db)

@app.cli.command('anonymizedb')
def anonymizedb_command():
    anonymize_db(db)

def flash_save_eventlog(unused_sender, message, category, **unused_extra):
    from lvfs.util import _event_log
    is_important = False
    if category in ['danger', 'warning']:
        is_important = True
    _event_log(str(message), is_important)

message_flashed.connect(flash_save_eventlog, app)

@lm.user_loader
def load_user(user_id):
    from lvfs.users.models import User
    g.user = db.session.query(User).filter(User.username == user_id).first()
    return g.user

@app.errorhandler(404)
def error_page_not_found(unused_msg=None):
    """ Error handler: File not found """

    # the world is a horrible place
    if request.path in ['/wp-login.php',
                        '/a2billing/common/javascript/misc.js']:
        return Response(response='bad karma', status=404, mimetype="text/plain")
    return render_template('error-404.html'), 404

@app.errorhandler(CSRFError)
def error_csrf(e):
    flash(str(e), 'danger')
    return redirect(url_for('main.route_dashboard'))
