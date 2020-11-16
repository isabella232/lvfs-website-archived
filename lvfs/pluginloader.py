#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+
#
# pylint: disable=too-few-public-methods,no-self-use

import os
import sys
from typing import List, Optional, Dict, Any

from cabarchive import CabArchive, CabFile
from jcat import JcatBlob

from .components.models import Component
from .firmware.models import Firmware
from .settings.models import Setting
from .tests.models import Test

class PluginError(Exception):
    pass

class PluginSettingText:

    def __init__(self, key: str, name: str, default: str = ''):
        self.key = key
        self.name = name
        self.default = default

class PluginSettingInteger:

    def __init__(self, key: str, name: str, default: int = 0):
        self.key = key
        self.name = name
        self.default = str(default)

class PluginSettingTextList:

    def __init__(self, key: str, name: str, default: Optional[List[str]] = None):
        self.key = key
        self.name = name
        if default:
            self.default = ','.join(default)
        else:
            self.default = ''

class PluginSettingBool:

    def __init__(self, key: str, name: str, default: bool = False):
        self.key = key
        self.name = name
        if default:
            self.default = 'enabled'
        else:
            self.default = 'disabled'

class PluginBase:

    def __init__(self, plugin_id: Optional[str] = None):
        self.id = plugin_id
        self.priority = 0
        self._setting_kvs: Dict[str, str] = {}
        self.name = 'Noname Plugin'
        self.summary = 'Plugin did not set summary'
        self.order_after: List[str] = []

    def file_modified(self, fn: str) -> None:
        raise NotImplementedError
    def metadata_sign(self, blob: bytes) -> JcatBlob:
        raise NotImplementedError
    def archive_sign(self, blob: bytes) -> bytes:
        raise NotImplementedError
    def archive_copy(self, cabarchive: CabArchive, cabfile: CabFile) -> None:
        raise NotImplementedError
    def archive_finalize(self, cabarchive: CabArchive, fw: Firmware) -> None:
        raise NotImplementedError
    def ensure_test_for_fw(self, fw: Firmware) -> None:
        raise NotImplementedError
    def oauth_logout(self) -> None:
        raise NotImplementedError
    def require_test_for_fw(self, fw: Firmware) -> bool:
        raise NotImplementedError
    def run_test_on_fw(self, test: Test, fw: Firmware) -> bool:
        raise NotImplementedError
    def require_test_for_md(self, md: Component) -> bool:
        raise NotImplementedError
    def run_test_on_md(self, test: Test, md: Component) -> bool:
        raise NotImplementedError

    def settings(self) -> List[Setting]:
        return []

    def get_setting(self, key: str, required: bool = False) -> str:
        from .util import _get_settings
        if self.id and not self._setting_kvs:
            self._setting_kvs = _get_settings(self.id.replace('-', '_'))
        if key not in self._setting_kvs:
            raise PluginError('No key %s' % key)
        if required and not self._setting_kvs[key]:
            raise PluginError('No value set for key %s' % key)
        return self._setting_kvs[key]

    def get_setting_bool(self, key: str) -> bool:
        if self.get_setting(key) == 'enabled':
            return True
        return False

    def get_setting_int(self, key: str) -> int:
        return int(self.get_setting(key))

    @property
    def enabled(self) -> bool:
        for setting in self.settings():
            if setting.name == 'Enabled':
                return self.get_setting_bool(setting.key)
        return True

    def __repr__(self) -> str:
        return "Plugin object %s" % self.id

class PluginGeneral(PluginBase):
    def __init__(self) -> None:
        PluginBase.__init__(self, 'general')
        self.name = 'General'
        self.summary = 'General server settings'

    def settings(self) -> List[Any]:
        s: List[Any] = []
        s.append(PluginSettingText('server_warning', 'Server Warning',
                                   'This is a test instance and may be broken at any time.'))
        s.append(PluginSettingText('firmware_baseuri', 'Firmware BaseURI',
                                   'https://fwupd.org/downloads/'))
        s.append(PluginSettingInteger('default_failure_minimum', 'Report failures required to demote', 5))
        s.append(PluginSettingInteger('default_failure_percentage', 'Report failures threshold for demotion', 70))
        return s

class Pluginloader:

    def __init__(self, dirname: str = '.'):
        self._dirname = dirname
        self._plugins: List[PluginBase] = []
        self.loaded = False

    def load_plugins(self) -> None:

        if self.loaded:
            return

        plugins = {}
        sys.path.insert(0, self._dirname)
        for f in os.listdir(self._dirname):
            location = os.path.join(self._dirname, f)
            if not os.path.isdir(location):
                continue
            location_init = os.path.join(location, '__init__.py')
            if not os.path.exists(location_init):
                continue
            mod = __import__(f)
            plugins[f] = mod.Plugin()
            if not plugins[f].id:
                plugins[f].id = f
        sys.path.pop(0)

        # depsolve
        for plugin_name in plugins:
            plugin = plugins[plugin_name]
            for name in plugin.order_after:
                if name not in plugins:
                    continue
                plugin2 = plugins[name]
                if not plugin2:
                    continue
                if plugin2.priority <= plugin.priority:
                    plugin.priority = plugin2.priority + 1

        # sort by priority
        for plugin in list(plugins.values()):
            self._plugins.append(plugin)
        self._plugins.sort(key=lambda x: x.priority)

        # general item
        self._plugins.insert(0, PluginGeneral())

        # success
        self.loaded = True

    def get_by_id(self, plugin_id: str) -> Optional[PluginBase]:
        if not self.loaded:
            self.load_plugins()
        for p in self._plugins:
            if p.id == plugin_id:
                return p
        return None

    def get_all(self) -> List[PluginBase]:
        if not self.loaded:
            self.load_plugins()
        return self._plugins

    # a file has been modified
    def file_modified(self, fn: str) -> None:
        if not self.loaded:
            self.load_plugins()
        for plugin in self._plugins:
            if not plugin.enabled:
                continue
            try:
                plugin.file_modified(fn)
            except PluginError as e:
                from .util import _event_log
                _event_log('Plugin %s failed for FileModifed(%s): %s' % (plugin.id, fn, str(e)))
            except NotImplementedError as _:
                pass

    # metadata is being built
    def metadata_sign(self, blob: bytes) -> List[JcatBlob]:
        if not self.loaded:
            self.load_plugins()
        blobs: List[JcatBlob] = []
        for plugin in self._plugins:
            if not plugin.enabled:
                continue
            try:
                blobs.append(plugin.metadata_sign(blob))
            except PluginError as e:
                from .util import _event_log
                _event_log('Plugin %s failed for MetadataSign(): %s' % (plugin.id, str(e)))
            except NotImplementedError as _:
                pass
        return blobs

    # an archive is being built
    def archive_sign(self, blob: bytes) -> List[bytes]:
        if not self.loaded:
            self.load_plugins()
        blobs: List[bytes] = []
        for plugin in self._plugins:
            if not plugin.enabled:
                continue
            try:
                blobs.append(plugin.archive_sign(blob))
            except PluginError as e:
                from .util import _event_log
                _event_log('Plugin %s failed for ArchiveSign(): %s' % (plugin.id, str(e)))
            except NotImplementedError as _:
                pass
        return blobs

    # an archive is being built
    def archive_copy(self, cabarchive: CabArchive, cabfile: CabFile) -> None:
        if not self.loaded:
            self.load_plugins()
        for plugin in self._plugins:
            if not plugin.enabled:
                continue
            try:
                plugin.archive_copy(cabarchive, cabfile)
            except PluginError as e:
                from .util import _event_log
                _event_log('Plugin %s failed for archive_copy(): %s' % (plugin.id, str(e)))
            except NotImplementedError as _:
                pass

    # an archive is being built
    def archive_finalize(self, cabarchive: CabArchive, fw: Firmware) -> None:
        if not self.loaded:
            self.load_plugins()
        for plugin in self._plugins:
            if not plugin.enabled:
                continue
            try:
                plugin.archive_finalize(cabarchive, fw)
            except PluginError as e:
                from .util import _event_log
                _event_log('Plugin %s failed for ArchiveFinalize(): %s' % (plugin.id, str(e)))
            except NotImplementedError as _:
                pass

    # ensure an test is added for the firmware
    def ensure_test_for_fw(self, fw: Firmware) -> None:
        if not self.loaded:
            self.load_plugins()
        for plugin in self._plugins:
            if not plugin.enabled:
                continue

            # allow plugins to set conditionals on ensuring
            ensure_test = False
            has_test_fw = False
            has_test_md = False
            try:
                if plugin.require_test_for_fw(fw):
                    ensure_test = True
                has_test_fw = True
            except NotImplementedError as _:
                pass
            try:
                for md in fw.mds:
                    if plugin.require_test_for_md(md):
                        ensure_test = True
                has_test_md = True
            except NotImplementedError as _:
                pass

            # any tests without either vfunc are assumed to always run
            if not has_test_md and not has_test_fw:
                ensure_test = True
            if not ensure_test:
                continue
            try:
                plugin.ensure_test_for_fw(fw)
            except PluginError as e:
                from .util import _event_log
                _event_log('Plugin %s failed for ensure_test_for_fw(): %s' % (plugin.id, str(e)))
            except NotImplementedError as _:
                pass

    # log out of all oauth providers
    def oauth_logout(self) -> None:
        if not self.loaded:
            self.load_plugins()
        for plugin in self._plugins:
            if not plugin.enabled:
                continue
            try:
                plugin.oauth_logout()
            except PluginError as e:
                from .util import _event_log
                _event_log('Plugin %s failed for oauth_logout(): %s' % (plugin.id, str(e)))
            except NotImplementedError as _:
                pass
