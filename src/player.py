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
    exit(1)
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
import threading
from datetime import datetime
from datetime import timedelta
from enum import Enum
import time


def sleep(milliseconds=1000):
    d = timedelta(milliseconds)
    t1 = datetime.now()
    while datetime.now() - t1 < d:
        Gtk.main_iteration()


class Status(Enum):
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2


class IdleObject(GObject.GObject):
    """
    Override GObject.GObject to always emit signals in the main thread
    by emmitting on an idle handler
    """
    def __init__(self):
        GObject.GObject.__init__(self)

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)


class Player(GObject.GObject):
    __gsignals__ = {
        'started': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'stopped': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'ended': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'paused': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        Gst.init_check(None)
        self.IS_GST010 = Gst.version()[0] == 0
        self.status = Status.STOPPED
        self.sound = None
        self.thread = None
        self.player = Gst.ElementFactory.make("playbin", "player")
        self.player.connect("about-to-finish", self.on_player_finished)
        bus = self.player.get_bus()
        bus.connect("message", self.on_player_message)

    def emit(self, *args):
        GObject.GObject.emit(self, *args)
        GLib.idle_add(GObject.GObject.emit, self, *args)

    def on_player_finished(self, player):
        self.status = Status.STOPPED
        self.emit('stopped', self.get_relative_position())
        self.emit('ended', self.get_relative_position())

    def on_player_message(self, bus, message):
        t = message.type
        print('---', t, '---')
        if t == Gst.Message.EOS:
            self.player.set_state(Gst.State.NULL)
        elif t == Gst.Message.ERROR:
            self.player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print("Error: %s" % err, debug)

    def set_sound(self, sound):
        self.sound = sound

    def __play(self):
        if self.sound is not None:
            self.player.set_property('uri', 'file://' + self.sound)
            self.player.set_state(Gst.State.PLAYING)
            self.status = Status.PLAYING
            self.emit('started', self.get_relative_position())

    def play(self):
        if self.status is Status.PAUSED:
            self.player.set_state(Gst.State.PLAYING)
            self.status = Status.PLAYING
            self.emit('started', self.get_relative_position())
        elif self.status is Status.STOPPED:
            self.thread = threading.Thread(target=self.__play, daemon=True)
            self.thread.start()

    def stop(self):
        if self.status is not Status.STOPPED:
            self.player.set_state(Gst.State.NULL)
            self.status = Status.STOPPED
            self.emit('stoped', self.get_relative_position())

    def pause(self):
        if self.status is Status.PLAYING:
            self.player.set_state(Gst.State.PAUSED)
            self.status = Status.PAUSED
            self.emit('paused', self.get_relative_position())

    def get_duration(self):
        if self.IS_GST010:
            duration_nanosecs = self.player.query_duration(Gst.Format.TIME)[2]
        else:
            duration_nanosecs = self.player.query_duration(Gst.Format.TIME)[1]
        duration = float(duration_nanosecs) / Gst.SECOND
        return duration

    def get_position(self):
        if self.IS_GST010:
            nanosecs = self.player.query_position(Gst.Format.TIME)[2]
        else:
            nanosecs = self.player.query_position(Gst.Format.TIME)[1]
        position = float(nanosecs) / Gst.SECOND
        return position

    def set_relative_position(self, position):
        if self.status is Status.PLAYING:
            if position >= 0 and position <= 100:
                nanosecs = int(position * self.get_duration() *
                               Gst.SECOND / 100.0)
                if self.status == Status.PLAYING:
                    was_playing = True
                    self.pause()
                else:
                    was_playing = False
                self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH,
                                        nanosecs)
                if was_playing:
                    self.play()

    def get_relative_position(self):
        if self.get_duration() == 0:
            return 0
        return int(100.0 * self.get_position() / self.get_duration())

    def __del__(self):
        self.stop()


if __name__ == '__main__':
    def fin(player, position, what):
        print(player, position, what)
    print(200)
    player2 = Player()
    player2.set_sound('/datos/Descargas/sample2.wav')
    player2.connect('started', fin, 'started')
    player2.connect('paused', fin, 'paused')
    player2.connect('stopped', fin, 'stopped')
    player2.play()
    print(1, player2.get_relative_position())
    time.sleep(2)
    player2.set_relative_position(50)
    print(2, player2.get_relative_position())
    time.sleep(5)
    print(3, player2.get_relative_position())
    exit(0)
