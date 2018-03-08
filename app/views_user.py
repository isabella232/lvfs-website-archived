#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
# Copyright (C) 2017 Richard Hughes <richard@hughsie.com>
# Licensed under the GNU General Public License Version 2

from flask import request, flash, url_for, redirect, render_template, g
from flask_login import login_required

from app import app, db

from .util import _error_internal, _error_permission_denied, _email_check
from .models import UserCapability, User, Vendor
from .hash import _password_hash

def _password_check(value):
    """ Check the password for suitability """
    success = True
    if len(value) < 8:
        success = False
        flash('The password is too short, the minimum is 8 characters', 'warning')
    if len(value) > 40:
        success = False
        flash('The password is too long, the maximum is 40 characters', 'warning')
    if value.lower() == value:
        success = False
        flash('The password requires at least one uppercase character', 'warning')
    if value.isalnum():
        success = False
        flash('The password requires at least one non-alphanumeric character', 'warning')
    return success

@app.route('/lvfs/user/<int:user_id>/modify', methods=['GET', 'POST'])
@login_required
def user_modify(user_id):
    """ Change details about the current user """

    # only accept form data
    if request.method != 'POST':
        return redirect(url_for('.profile'))

    # security check
    if g.user.user_id != user_id:
        return _error_permission_denied('Unable to modify a different user')
    if g.user.auth_type == 'local+locked':
        return _error_permission_denied('Unable to change user as account locked')
    if g.user.auth_type == 'oauth':
        return _error_permission_denied('Unable to change OAuth-only user')

    # check we got enough data
    if not 'password_new' in request.form:
        return _error_permission_denied('Unable to change user as no data')
    if not 'password_old' in request.form:
        return _error_permission_denied('Unable to change user as no data')
    if not 'display_name' in request.form:
        return _error_permission_denied('Unable to change user as no data')
    old_password_hash = _password_hash(request.form['password_old'])
    user = db.session.query(User).\
            filter(User.user_id == user_id).\
            filter(User.password == old_password_hash).first()
    if not user:
        flash('Failed to modify profile: Incorrect existing password', 'danger')
        return redirect(url_for('.profile'), 302)

    # check password
    password = request.form['password_new']
    if not _password_check(password):
        return redirect(url_for('.profile'), 302)

    # verify name
    display_name = request.form['display_name']
    if len(display_name) < 3:
        flash('Failed to modify profile: Name invalid', 'warning')
        return redirect(url_for('.profile'), 302)

    # save to database
    user.password = _password_hash(password)
    user.display_name = display_name
    db.session.commit()
    flash('Updated profile', 'info')
    return redirect(url_for('.profile'))

@app.route('/lvfs/user/<int:user_id>/modify_by_admin', methods=['POST'])
@login_required
def user_modify_by_admin(user_id):
    """ Change details about the any user """

    # check exists
    user = db.session.query(User).filter(User.user_id == user_id).first()
    if not user:
        return _error_internal('No user with that user_id', 422)

    # security check
    if not g.user.check_for_vendor(user.vendor):
        return _error_permission_denied('Unable to modify user as non-admin')

    # set each optional thing in turn
    for key in ['display_name', 'username', 'auth_type']:
        if key in request.form:
            setattr(user, key, request.form[key])

    # unchecked checkbuttons are not included in the form data
    for key in ['is_qa', 'is_analyst', 'is_vendor_manager']:
        setattr(user, key, True if key in request.form else False)

    # password is optional, and hashed
    if 'password' in request.form and request.form['password']:
        user.password = _password_hash(request.form['password'])

    db.session.commit()
    flash('Updated profile', 'info')
    return redirect(url_for('.user_admin', user_id=user_id))

@app.route('/lvfs/user/add', methods=['GET', 'POST'])
@login_required
def user_add():
    """ Add a user [ADMIN ONLY] """

    # only accept form data
    if request.method != 'POST':
        return redirect(url_for('.profile'))

    # security check
    if not g.user.check_capability(UserCapability.Admin):
        return _error_permission_denied('Unable to add user as non-admin')

    if not 'username' in request.form:
        return _error_permission_denied('Unable to add user as no username')
    if not 'password_new' in request.form:
        return _error_permission_denied('Unable to add user as no password_new')
    if not 'group_id' in request.form:
        return _error_permission_denied('Unable to add user as no group_id')
    if not 'display_name' in request.form:
        return _error_permission_denied('Unable to add user as no display_name')
    user = db.session.query(User).filter(User.username == request.form['username']).first()
    if user:
        return _error_internal('Already a user with that username', 422)

    # verify password
    password = request.form['password_new']
    if not _password_check(password):
        return redirect(url_for('.user_list'), 302)

    # verify email
    username = request.form['username']
    if not _email_check(username):
        flash('Failed to add user: Invalid email address', 'warning')
        return redirect(url_for('.user_list'), 302)

    # verify group_id
    group_id = request.form['group_id']
    if len(group_id) < 3:
        flash('Failed to add user: QA group invalid', 'warning')
        return redirect(url_for('.user_list'), 302)

    # verify name
    display_name = request.form['display_name']
    if len(display_name) < 3:
        flash('Failed to add user: Name invalid', 'warning')
        return redirect(url_for('.user_list'), 302)

    vendor = db.session.query(Vendor).filter(Vendor.group_id == group_id).first()
    if not vendor:
        vendor = Vendor(group_id)
        db.session.add(vendor)
        db.session.commit()
    user = User(username=username,
                password=_password_hash(password),
                display_name=display_name,
                vendor_id=vendor.vendor_id)
    db.session.add(user)
    db.session.commit()
    flash('Added user %i' % user.user_id, 'info')
    return redirect(url_for('.user_list'), 302)

@app.route('/lvfs/user/<int:user_id>/delete')
@login_required
def user_delete(user_id):
    """ Delete a user """

    # security check
    if not g.user.check_capability(UserCapability.Admin):
        return _error_permission_denied('Unable to remove user as not admin')

    # check whether exists in database
    user = db.session.query(User).filter(User.user_id == user_id).first()
    if not user:
        flash('Failed to delete user: No user found', 'danger')
        return redirect(url_for('.user_list'), 422)
    db.session.delete(user)
    db.session.commit()
    flash('Deleted user', 'info')
    return redirect(url_for('.user_list'), 302)

@app.route('/lvfs/userlist')
@login_required
def user_list():
    """
    Show a list of all users
    """
    if not g.user.check_capability(UserCapability.Admin):
        return _error_permission_denied('Unable to show userlist for non-admin user')
    return render_template('userlist.html', users=db.session.query(User).all())

@app.route('/lvfs/user/<int:user_id>/admin')
@login_required
def user_admin(user_id):
    """
    Shows an admin panel for a user
    """

    # check exists
    user = db.session.query(User).filter(User.user_id == user_id).first()
    if not user:
        flash('No user found', 'danger')
        return redirect(url_for('.user_list'), 422)

    # check user is not trying to edit themselves using the admin panel
    if user.user_id == g.user.user_id:
        flash('Cannot self edit using admin panel', 'warning')
        return redirect(url_for('.user_list'))

    # security check
    if not g.user.check_for_vendor(user.vendor):
        return _error_permission_denied('Unable to modify user for non-admin user')

    return render_template('useradmin.html', u=user)
