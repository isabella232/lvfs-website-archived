#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Richard Hughes <richard@hughsie.com>
# Licensed under the GNU General Public License Version 2

from __future__ import print_function

import os
import boto3

from app.pluginloader import PluginBase, PluginError, PluginSettingText

from app import db

class Plugin(PluginBase):
    def __init__(self):
        PluginBase.__init__(self)

    def order_after(self):
        return ['sign-gpg']

    def name(self):
        return 'CDN'

    def settings(self):
        s = []
        s.append(PluginSettingText('cdn_sync_folder', 'Folder', 'downloads'))
        s.append(PluginSettingText('cdn_sync_bucket', 'Bucket', 'lvfstestbucket'))
        s.append(PluginSettingText('cdn_sync_region', 'Region', 'us-east-1'))
        s.append(PluginSettingText('cdn_sync_username', 'Username', 'aws_access_key_id'))
        s.append(PluginSettingText('cdn_sync_password', 'Password', 'aws_secret_access_key'))
        s.append(PluginSettingText('cdn_sync_files', 'File Whitelist',
                                   'firmware.xml.gz,firmware.xml.gz.asc,"'
                                   'firmware-testing.xml.gz,firmware-testing.xml.gz.asc'))
        return s

    def file_modified(self, fn):

        # is the file in the whitelist
        settings = db.settings.get_filtered('cdn_sync_')
        fns = settings['files']
        if not fns:
            return
        basename = os.path.basename(fn)
        if basename not in fns.split(','):
            print('%s not in %s' % (basename, fns))
            return

        # bucket not set
        if 'bucket' not in settings:
            return
        if not settings['bucket']:
            return

        # upload
        try:
            key = os.path.join(settings['folder'], os.path.basename(fn))
            session = boto3.Session(aws_access_key_id=settings['username'],
                                    aws_secret_access_key=settings['password'],
                                    region_name=settings['region'])
            s3 = session.resource('s3')
            bucket = s3.Bucket(settings['bucket'])
            bucket.Acl().put(ACL='public-read')
            print("uploading %s as %s" % (fn, key))
            blob = open(fn, 'rb').read()
            obj = bucket.put_object(Key=key, Body=blob)
            obj.Acl().put(ACL='public-read')
        except BaseException as e:
            raise PluginError(e)
