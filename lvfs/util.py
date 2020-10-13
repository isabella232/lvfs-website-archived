#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=wrong-import-position

import json
import calendar
import datetime
import string
import random
import subprocess
import tempfile

from typing import Optional, Dict, List, Tuple, Any

from functools import wraps

from lxml import etree as ET
from flask import request, flash, render_template, g, Response, redirect, url_for

def _fix_component_name(name: Optional[str],
                        developer_name: Optional[str] = None) -> Optional[str]:
    if not name:
        return None

    # things just to nuke
    for nuke in ['(R)']:
        name = name.replace(nuke, '')

    words_new = []
    words_banned = ['firmware', 'update', 'system', 'device', 'bios', 'me',
                    'embedded', 'controller']
    if developer_name:
        words_banned.append(developer_name.lower())
    for word in name.split(' '):
        if not word:
            continue
        if word.lower() not in words_banned:
            words_new.append(word)
    return ' '.join(words_new)

def _is_hex(chunk: str) -> bool:
    try:
        _ = int(chunk, 16)
    except ValueError as _:
        return False
    return True

def _validate_guid(guid: str) ->bool:
    """ Validates if the string is a valid GUID """
    if not guid:
        return False
    if guid.lower() != guid:
        return False
    split = guid.split('-')
    if len(split) != 5:
        return False
    if len(split[0]) != 8 or not _is_hex(split[0]):
        return False
    if len(split[1]) != 4 or not _is_hex(split[1]):
        return False
    if len(split[2]) != 4 or not _is_hex(split[2]):
        return False
    if len(split[3]) != 4 or not _is_hex(split[3]):
        return False
    if len(split[4]) != 12 or not _is_hex(split[4]):
        return False
    return True

def _unwrap_xml_text(txt: str) -> str:
    txt = txt.replace('\r', '')
    new_lines = []
    for line in txt.split('\n'):
        if not line:
            continue
        new_lines.append(line.strip())
    return ' '.join(new_lines)

def _markdown_from_root(root: ET.SubElement) -> str:
    """ return MarkDown for the XML input """
    tmp = ''
    for n in root:
        if n.tag == 'p':
            if list(n):
                raise KeyError('Invalid XML, found child of {}'.format(n.tag))
            if n.text:
                tmp += _unwrap_xml_text(n.text) + '\n\n'
        elif n.tag == 'ul' or n.tag == 'ol':
            for c in n:
                if c.tag == 'li':
                    if list(c):
                        raise KeyError('Invalid XML, found child of {}'.format(c.tag))
                    if c.text:
                        tmp += ' * ' + _unwrap_xml_text(c.text) + '\n'
                else:
                    raise KeyError('Invalid XML, got {}'.format(c.tag))
            tmp += '\n'
        else:
            raise KeyError('Invalid XML, got {}'.format(n.tag))
    tmp = tmp.strip(' \n')
    return tmp

def _check_is_markdown_li(line: str) -> int:
    if line.startswith('- '):
        return 2
    if line.startswith(' - '):
        return 3
    if line.startswith('* '):
        return 2
    if line.startswith(' * '):
        return 3
    if len(line) > 2 and line[0].isdigit() and line[1] == '.':
        return 2
    if len(line) > 3 and line[0].isdigit() and line[1].isdigit() and line[2] == '.':
        return 3
    return 0

def _xml_from_markdown(markdown: str) -> Optional[ET.Element]:
    """ return a ElementTree for the markdown text """
    if not markdown:
        return None
    ul = None
    root = ET.Element('description')
    for line in markdown.split('\n'):
        line = line.strip()
        if not line:
            continue
        markdown_li_sz = _check_is_markdown_li(line)
        if markdown_li_sz:
            if ul is None:
                ul = ET.SubElement(root, 'ul')
            ET.SubElement(ul, 'li').text = line[markdown_li_sz:].strip()
        else:
            ul = None
            ET.SubElement(root, 'p').text = line
    return root

def _get_settings(prefix: str = None) -> Dict[str, str]:
    """ return a dict of all the settings """
    from lvfs import db
    from lvfs.settings.models import Setting
    settings = {}
    stmt = db.session.query(Setting)
    if prefix:
        stmt = stmt.filter(Setting.key.startswith(prefix))
    for setting in stmt:
        settings[setting.key] = setting.value
    return settings

def _get_sanitized_basename(basename: str) -> str:
    basename_sane = basename.encode('ascii', 'ignore').decode('utf-8')
    for key, value in [(',', '_')]:
        basename_sane = basename_sane.replace(key, value)
    return basename_sane

def _get_client_address() -> str:
    """ Gets user IP address """
    try:
        if request.headers.getlist("X-Forwarded-For"):
            return request.headers.getlist("X-Forwarded-For")[0]
        if not request.remote_addr:
            return '127.0.0.1'
        return request.remote_addr
    except RuntimeError as _:
        return '127.0.0.1'

def _event_log(msg: str, is_important: bool = False) -> None:
    """ Adds an item to the event log """
    user_id = 2 	# Anonymous User
    vendor_id = 1	# admin
    request_path = None
    if hasattr(g, 'user') and g.user:
        user_id = g.user.user_id
        vendor_id = g.user.vendor_id
    if request:
        request_path = request.path
    from lvfs.main.models import Event
    from lvfs import db
    event = Event(user_id=user_id,
                  message=msg,
                  vendor_id=vendor_id,
                  address=_get_client_address(),
                  request=request_path,
                  is_important=is_important)
    db.session.add(event)
    db.session.commit()

def _error_internal(msg: str = None, errcode:int = 402) -> Tuple[str, int]:
    """ Error handler: Internal """
    flash("Internal error: %s" % msg, 'danger')
    return render_template('error.html'), errcode

def _json_success(msg: str = None, uri: str = None, errcode:int = 200) -> Response:
    """ Success handler: JSON output """
    item: Dict[str, Any] = {}
    item['success'] = True
    if msg:
        item['msg'] = msg
    if uri:
        item['uri'] = uri
    dat = json.dumps(item, sort_keys=True, indent=4, separators=(',', ': '))
    return Response(response=dat,
                    status=errcode, \
                    mimetype="application/json")

def _json_error(msg: str = None, errcode:int = 400) -> Response:
    """ Error handler: JSON output """
    item: Dict[str, Any] = {}
    item['success'] = False
    if msg:
        item['msg'] = str(msg)
    dat = json.dumps(item, sort_keys=True, indent=4, separators=(',', ': '))
    return Response(response=dat,
                    status=errcode, \
                    mimetype="application/json")

def _get_chart_labels_months(ts: int = 1) -> List[str]:
    """ Gets the chart labels """
    now = datetime.date.today()
    labels = []
    for i in range(0, 12 * ts):
        then = now - datetime.timedelta((i + 1) * 30)
        labels.append('{} {}'.format(calendar.month_name[then.month], then.year))
    return labels

def _get_chart_labels_days(limit:int = 30) -> List[str]:
    """ Gets the chart labels """
    now = datetime.date.today()
    labels = []
    for i in range(0, limit):
        then = now - datetime.timedelta(i + 1)
        labels.append("%02i-%02i-%02i" % (then.year, then.month, then.day))
    return labels

def _get_chart_labels_hours() -> List[str]:
    """ Gets the chart labels """
    labels = []
    for i in range(0, 24):
        labels.append("%02i" % i)
    return labels

def _email_check(value: str) -> bool:
    """ Do a quick and dirty check on the email address """
    if len(value) < 5 or value.find('@') == -1 or value.find('.') == -1:
        return False
    return True

def _generate_password(size: int = 10,
                       chars: str = string.ascii_letters + string.digits) -> str:
    return ''.join(random.choice(chars) for _ in range(size))

def _get_certtool() -> List[str]:
    from lvfs import app
    return app.config['CERTTOOL'].split(' ')

def _pkcs7_certificate_info(text: str) -> Dict[str, str]:

    # write certificate to temp file
    crt = tempfile.NamedTemporaryFile(mode='wb',
                                      prefix='pkcs7_',
                                      suffix=".p7b",
                                      dir=None,
                                      delete=True)
    crt.write(text.encode('utf8'))
    crt.flush()

    # get signature
    argv = _get_certtool() + ['--certificate-info', '--infile', crt.name]
    ps = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = ps.communicate()
    if ps.returncode != 0:
        raise IOError(err)
    info = {}
    for line in out.decode('utf8').split('\n'):
        try:
            key, value = line.strip().split(':', 2)
            if key == 'Serial Number (hex)':
                info['serial'] = value.strip()
        except ValueError as _:
            pass
    return info

def _pkcs7_signature_info(text: str, check_rc: bool = True) -> Dict[str, str]:

    # write signature to temp file
    sig = tempfile.NamedTemporaryFile(mode='wb',
                                      prefix='pkcs7_',
                                      suffix=".txt",
                                      dir=None,
                                      delete=True)
    sig.write(text.encode('utf8'))
    sig.flush()

    # parse
    argv = _get_certtool() + ['--p7-verify', '--infile', sig.name]
    ps = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = ps.communicate()
    if check_rc and ps.returncode != 0:
        raise IOError(out, err)
    info = {}
    for line in out.decode('utf8').split('\n'):
        try:
            key, value = line.strip().split(':', 2)
            if key == 'Signer\'s serial':
                info['serial'] = value.strip()
        except ValueError as _:
            pass
    return info

def _pkcs7_signature_verify(certificate: str,
                            payload: str,
                            signature: str) -> bool:

    # check the signature against the client cert
    crt = tempfile.NamedTemporaryFile(mode='wb',
                                      prefix='pkcs7_',
                                      suffix=".p7b",
                                      dir=None,
                                      delete=True)
    crt.write(certificate.encode('utf8'))
    crt.flush()

    # write payload to temp file
    pay = tempfile.NamedTemporaryFile(mode='wb',
                                      prefix='pkcs7_',
                                      suffix=".json",
                                      dir=None,
                                      delete=True)
    pay.write(payload.encode('utf8'))
    pay.flush()

    # write signature to temp file
    sig = tempfile.NamedTemporaryFile(mode='wb',
                                      prefix='pkcs7_',
                                      suffix=".p7b",
                                      dir=None,
                                      delete=True)
    sig.write(signature.encode('utf8'))
    sig.flush()

    # verify
    status = None
    argv = _get_certtool() + ['--p7-verify',
                              '--load-certificate', crt.name,
                              '--infile', sig.name,
                              '--load-data', pay.name]
    ps = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _, err = ps.communicate()
    if ps.returncode != 0:
        raise IOError(err)
    for line in err.decode('utf8').split('\n'):
        try:
            key, value = line.strip().split(':', 1)
            print(key, value)
            if key == 'Signature status':
                status = value.strip()
        except ValueError as _:
            pass
    return status == 'ok'

def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user.check_acl('@admin'):
            flash('Only the admin team can access this resource', 'danger')
            return redirect(url_for('main.route_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def _get_datestr_from_datetime(when):
    return int("%04i%02i%02i" % (when.year, when.month, when.day))

def _is_keyword_valid(value: str) -> bool:
    if not len(value):
        return False
    if value.find('.') != -1:
        return False
    if value in ['a',
                 'bios',
                 'company',
                 'corporation',
                 'development',
                 'device',
                 'firmware',
                 'for',
                 'limited',
                 'system',
                 'the',
                 'update']:
        return False
    return True

def _sanitize_keyword(value: str) -> str:
    for rpl in ['(', ')', '[', ']', '*', '?']:
        value = value.replace(rpl, '')
    return value.strip().lower()

def _split_search_string(value: str) -> List[str]:
    for delim in ['/', ',']:
        value = value.replace(delim, ' ')
    keywords: List[str] = []
    for word in value.split(' '):
        keyword = _sanitize_keyword(word)
        if not _is_keyword_valid(keyword):
            continue
        if keyword in keywords:
            continue
        keywords.append(keyword)
    return keywords
