#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# utils.py
#
# This file is part of uPodcatcher
#
# Copyright (C) 2014
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
    gi.require_version('GLib', '2.0')
    gi.require_version('GObject', '2.0')
except Exception as e:
    print(e)
    exit(1)
from gi.repository import GLib
from gi.repository import GObject
import threading
import requests


class Downloader(threading.Thread, GObject.GObject):
    __gsignals__ = {
        'started': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
        'ended': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
        'failed': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, url, filename):
        threading.Thread.__init__(self)
        GObject.GObject.__init__(self)
        self.url = url
        self.filename = filename
        self.daemon = True

    def emit(self, *args):
        # GObject.GObject.emit(self, *args)
        GObject.idle_add(GObject.GObject.emit, self, *args)
        # GLib.idle_add(GObject.GObject.emit, self, *args)

    def run(self):
        try:
            self.emit('started')
            r = requests.get(self.url, stream=True)
            with open(self.filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            self.emit('ended')
        except Exception as e:
            print(e)
            self.emit('failed')
