#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# addfeeddialog.py
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
    gi.require_version('Gtk', '3.0')
except Exception as e:
    print(e)
    exit(1)
from gi.repository import Gtk
import comun
from comun import _


class AddFeedDialog(Gtk.Dialog):
    """docstring for AddFeedDialog"""
    def __init__(self, window):
        #
        Gtk.Dialog.__init__(self, '{0} | {1}'.format(comun.APPNAME,
                                                     _('Add Podcast')),
                            window,
                            Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT,
                             Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_icon_from_file(comun.ICON)

        frame = Gtk.Frame()
        frame.set_margin_top(10)
        frame.set_margin_bottom(10)
        frame.set_margin_left(10)
        frame.set_margin_right(10)
        self.get_content_area().add(frame)
        grid = Gtk.Grid()
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_margin_left(10)
        grid.set_margin_right(10)
        frame.add(grid)
        grid.attach(Gtk.Label(_('Feed') + ': '), 0, 0, 1, 1)
        self.entry = Gtk.Entry()
        self.entry.set_width_chars(30)
        grid.attach(self.entry, 1, 0, 1, 1)

        self.show_all()

    def get_url(self):
        return self.entry.get_text()


if __name__ == "__main__":
    afd = AddFeedDialog()
    if afd.run() == Gtk.ResponseType.ACCEPT:
        print(afd.get_url())
    afd.destroy()
    exit(0)
