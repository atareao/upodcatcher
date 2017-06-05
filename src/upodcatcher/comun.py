#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# comun.py
#
# This file is part of upodcatcher
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

import os
import locale
import gettext

__author__ = 'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'
__copyright__ = 'Copyright (c) 2017 Lorenzo Carbonell'
__license__ = 'GPLV3'
__url__ = 'http://www.atareao.es'
USRDIR = '/usr'


def is_package():
    return (__file__.startswith(USRDIR) or os.getcwd().startswith(USRDIR))


PARAMS = {'first-time': True,
          'version': '',
          'autostart': False,
          'theme': 'light',
          'session_length': 25,
          'break_length': 5,
          'long_break_length': 20,
          'number_of_pomodoros': 4,
          'play_sounds': True,
          'session_sound_file': 'default',
          'break_sound_file': 'default'
          }


APP = 'upodcatcher'
APPCONF = APP + '.conf'
APPDATA = APP + '.data'
APPNAME = 'uPodcatcher'
CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.config')
CONFIG_APP_DIR = os.path.join(CONFIG_DIR, APP)
PODCASTS_DIR = os.path.join(CONFIG_APP_DIR, 'podcasts')
THUMBNAILS_DIR = os.path.join(CONFIG_APP_DIR, 'thumbnails')
CONFIG_FILE = os.path.join(CONFIG_APP_DIR, APPCONF)
DATABASE = os.path.join(CONFIG_APP_DIR, 'feeds.db')
AUTOSTART_DIR = os.path.join(CONFIG_DIR, 'autostart')
FILE_AUTO_START = os.path.join(AUTOSTART_DIR,
                               'upodocatcher-autostart.desktop')
if not os.path.exists(CONFIG_APP_DIR):
    os.makedirs(CONFIG_APP_DIR)
if not os.path.exists(PODCASTS_DIR):
    os.makedirs(PODCASTS_DIR)
if not os.path.exists(THUMBNAILS_DIR):
    os.makedirs(THUMBNAILS_DIR)

if is_package():
    ROOTDIR = '/usr/share/'
    if 'SNAP' in os.environ:
        ROOTDIR = os.environ["SNAP"] + ROOTDIR
    LANGDIR = os.path.join(ROOTDIR, 'locale-langpack')
    APPDIR = os.path.join(ROOTDIR, APP)
    ICONDIR = os.path.join(APPDIR, 'icons')
    CHANGELOG = os.path.join(APPDIR, 'changelog')
    FILE_AUTO_START_ORIG = os.path.join(APPDIR,
                                        'upodcatcher-autostart.desktop')
else:
    ROOTDIR = os.path.dirname(__file__)
    LANGDIR = os.path.join(ROOTDIR, 'template1')
    APPDIR = os.path.join(ROOTDIR, APP)

    ICONDIR = os.path.normpath(os.path.join(ROOTDIR, '../../data/icons'))
    DEBIANDIR = os.path.normpath(os.path.join(ROOTDIR, '../../debian'))
    CHANGELOG = os.path.join(DEBIANDIR, 'changelog')
    FILE_AUTO_START_ORIG = os.path.join(os.path.normpath(os.path.join(
        ROOTDIR, '../data')), 'upodcatcher-autostart.desktop')
PLAY_ICON = os.path.join(ICONDIR, 'play.svg')
PAUSE_ICON = os.path.join(ICONDIR, 'pause.svg')
WAIT_ICON = os.path.join(ICONDIR, 'wait.svg')
DOWNLOAD_ICON = os.path.join(ICONDIR, 'download.svg')
DELETE_ICON = os.path.join(ICONDIR, 'delete.svg')
INFO_ICON = os.path.join(ICONDIR, 'info.svg')
NOIMAGE_ICON = os.path.join(ICONDIR, 'podcastnoimage.svg')
LISTENED_ICON = os.path.join(ICONDIR, 'listened.svg')
NOLISTENED_ICON = os.path.join(ICONDIR, 'nolistened.svg')
DOWNLOAD_ANIM = os.path.join(ICONDIR, 'loading.gif')
ICON = os.path.join(ICONDIR, 'upodcatcher.svg')


f = open(CHANGELOG, 'r')
line = f.readline()
f.close()
pos = line.find('(')
posf = line.find(')', pos)
VERSION = line[pos + 1:posf].strip()
if not is_package():
    VERSION = VERSION + '-src'

try:
    current_locale, encoding = locale.getdefaultlocale()
    language = gettext.translation(APP, LANGDIR, [current_locale])
    language.install()
    _ = language.gettext
except Exception as e:
    _ = str
