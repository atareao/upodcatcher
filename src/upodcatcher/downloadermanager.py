#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# downloadermanager.py
#
# This file is part of uPodcatcher
#
# Copyright (C) 2017
# Lorenzo Carbonell Cerezo <lorenzo.carbonell.cerezo@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import gi
try:
    gi.require_version('GObject', '2.0')
    gi.require_version('GLib', '2.0')
except Exception as e:
    print(e)
    exit(1)
from gi.repository import GObject
from gi.repository import GLib
import os
from .downloader import Downloader
from . import comun


class DownloaderManager(GObject.GObject):
    __gsignals__ = {
        'started': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (object,)),
        'ended': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (object,)),
        'failed': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (object,)),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.downloader = None
        self.queue = []
        self.tries = 0

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)

    def on_downloader_ended(self, widget, row):
        self.emit('ended', row)
        if len(self.queue) > 0:
            new_row = self.queue.pop()
            self.download(new_row)
        else:
            self.downloader = None

    def on_downloader_failed(self, widget, row):
        self.emit('failed', row)
        if self.tries < 3:
            self.queue.insert(0, row)
        else:
            self.tries = 0
        if len(self.queue) > 0:
            new_row = self.queue.pop()
            if new_row == row:
                self.tries += 1
            self.download(new_row)
        else:
            self.downloader = None

    def add(self, row):
        if self.downloader is None:
            self.download(row)
        else:
            self.queue.insert(0, row)

    def download(self, row):
        url = row.data['url']
        ext = 'mp3'
        filename = os.path.join(comun.PODCASTS_DIR,
                                'podcast_{0}.{1}'.format(
                                    row.data['id'],
                                    ext))
        self.downloader = Downloader(url, filename)
        self.downloader.connect('ended', self.on_downloader_ended, row)
        self.downloader.connect('failed', self.on_downloader_failed, row)
        self.downloader.run()
        self.emit('started', row)
