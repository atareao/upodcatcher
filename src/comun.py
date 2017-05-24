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


######################################

def is_package():
    return not os.path.dirname(os.path.abspath(__file__)).endswith('src')

######################################


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
DATA_FILE = os.path.join(CONFIG_APP_DIR, APPDATA)
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
    SOCIALDIR = os.path.join(APPDIR, 'social')
    SOUNDIR = os.path.join(APPDIR, 'sounds')
    CHANGELOG = os.path.join(APPDIR, 'changelog')
    FILE_AUTO_START_ORIG = os.path.join(APPDIR,
                                        'upodcatcher-autostart.desktop')
else:
    ROOTDIR = os.path.dirname(__file__)
    LANGDIR = os.path.join(ROOTDIR, 'template1')
    APPDIR = os.path.join(ROOTDIR, APP)
    DATADIR = os.path.normpath(os.path.join(ROOTDIR, '../data'))
    ICONDIR = os.path.normpath(os.path.join(ROOTDIR, '../data/icons'))
    SOCIALDIR = os.path.normpath(os.path.join(ROOTDIR, '../data/social'))
    SOUNDIR = os.path.normpath(os.path.join(ROOTDIR, '../data/sounds'))
    DEBIANDIR = os.path.normpath(os.path.join(ROOTDIR, '../debian'))
    CHANGELOG = os.path.join(DEBIANDIR, 'changelog')
    FILE_AUTO_START_ORIG = os.path.join(os.path.normpath(os.path.join(
        ROOTDIR, '../data')), 'upodcatcher-autostart.desktop')
UI_FILE = os.path.join(DATADIR, 'ui.xml')
PLAY_ICON = os.path.join(ICONDIR, 'play.svg')
PAUSE_ICON = os.path.join(ICONDIR, 'pause.svg')
LITTLE_PLAY_ICON = os.path.join(ICONDIR, 'lplay.svg')
LITTLE_PAUSE_ICON = os.path.join(ICONDIR, 'lpause.svg')
DOWNLOAD_ICON = os.path.join(ICONDIR, 'download.svg')
BACKWARD_ICON = os.path.join(ICONDIR, 'backward.svg')
STEP_BACKWARD_ICON = os.path.join(ICONDIR, 'step_backward.svg')
FORWARD_ICON = os.path.join(ICONDIR, 'forward.svg')
STEP_FORWARD_ICON = os.path.join(ICONDIR, 'step_forward.svg')
NOIMAGE_ICON = os.path.join(ICONDIR, 'podcastnoimage.svg')
DOWNLOAD_ANIM = os.path.join(ICONDIR, 'loading.gif')
ICON = os.path.join(ICONDIR, 'upodcatcher.svg')
DATABASE = os.path.join(DATADIR, 'feeds.db')

'''
f = open(CHANGELOG, 'r')
line = f.readline()
f.close()
pos = line.find('(')
posf = line.find(')', pos)
VERSION = line[pos + 1:posf].strip()
if not is_package():
    VERSION = VERSION + '-src'
'''
try:
    current_locale, encoding = locale.getdefaultlocale()
    language = gettext.translation(APP, LANGDIR, [current_locale])
    language.install()
    _ = language.gettext
except Exception as e:
    _ = str
