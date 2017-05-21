#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# player.py
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

import gi
try:
    gi.require_version('Gst', '1.0')
    gi.require_version('Gtk', '3.0')
    gi.require_version('GLib', '2.0')
    gi.require_version('GObject', '2.0')
except Exception as e:
    print(e)
    exit(-1)
from gi.repository import Gst
from gi.repository import GLib
from gi.repository import GObject
from enum import Enum
import mimetypes
from ctypes import *

mimetypes.init()


class Status(Enum):
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2


class Player(GObject.GObject):
    __gsignals__ = {
        'started': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'stopped': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'paused': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        Gst.init_check(None)
        self.status = Status.STOPPED
        self.player = None

    def get_player(self):
        player = Gst.parse_launch('uridecodebin name=urisrc !\
 audioconvert ! audioresample ! queue ! speed name=speed !\
 volume name=volume ! equalizer-10bands name=equalizer ! autoaudiosink')
        bus = player.get_bus()
        bus.add_signal_watch()
        bus.connect('message::state-changed', self.on_state_changed)
        bus.connect('message', self.on_player_message)
        return player

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)

    def on_player_message(self, bus, message):
        t = message.type
        # print('---', t, '---')
        if t == Gst.MessageType.EOS:
            self.player.set_state(Gst.State.NULL)
        elif t == Gst.MessageType.ERROR:
            self.player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print('Error: %s' % err, debug)

    def on_state_changed(self, bus, msg):
        old, new, pending = msg.parse_state_changed()
        # print(old, new, pending)

    def set_filename(self, filename):
        if self.player is not None:
            self.player.set_state(Gst.State.NULL)
        self.player = self.get_player()
        self.player.get_by_name('urisrc').set_property('uri', 'file://'+filename)

    def play(self):
        '''Play'''
        self.player.set_state(Gst.State.PLAYING)
        self.status = Status.PLAYING
        self.emit('started', self.get_position())

    def pause(self):
        '''Pause'''
        self.player.set_state(Gst.State.PAUSED)
        self.status = Status.PAUSED
        self.emit('paused', self.get_position())

    def stop(self):
        '''Stop'''
        if self.player is not None:
            self.player.set_state(Gst.State.READY)
            self.status = Status.STOPPED
            self.emit('stopped', self.get_position())

    def set_volume(self, volume):
        if self.player is not None:
            self.player.get_by_name('volume').set_property('volume', volume)

    def set_speed(self, speed):
        if self.player is not None:
            self.player.get_by_name('speed').set_property('speed', speed)

    def set_position(self, position):
        self.player.get_state(Gst.CLOCK_TIME_NONE)
        try:
            assert self.player.seek_simple(Gst.Format.TIME,
                                           Gst.SeekFlags.FLUSH,
                                           position * Gst.SECOND)
        except AssertionError as e:
            print(e)

    def get_duration(self):
        duration_nanosecs = self.player.query_duration(Gst.Format.TIME)[1]
        duration = float(duration_nanosecs) / Gst.SECOND
        return duration

    def get_position(self):
        nanosecs = self.player.query_position(Gst.Format.TIME)[1]
        position = float(nanosecs) / Gst.SECOND
        return position


if __name__ == '__main__':
    import time
    def fin(player, position, what):
        print(player, position, what)
    print('start')
    player = Player()
    player.set_filename('/datos/Descargas/test.ogg')
    player.play()
    player.set_speed(2)
    time.sleep(2)
    player.pause()
    time.sleep(2)
    player.play()
    time.sleep(2)
    player.set_filename('/home/lorenzo/Descargas/sample.mp3')
    player.connect('started', fin, 'started')
    player.connect('paused', fin, 'paused')
    player.connect('stopped', fin, 'stopped')
    player.set_speed(1)
    player.play()
    time.sleep(2)
    player.set_position(10)
    time.sleep(2)
    player.set_position(50)
    time.sleep(2)
