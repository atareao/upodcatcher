#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# foundpodcastdialog.py
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
    gi.require_version('Gtk', '3.0')
    gi.require_version('GdkPixbuf', '2.0')
except Exception as e:
    print(e)
    exit(-1)
from gi.repository import Gtk
from gi.repository import GdkPixbuf
from utils import get_pixbuf_from_base64string
import comun
from comun import _


class PodcastFoundRow(Gtk.ListBoxRow):
    def __init__(self, data):
        super(Gtk.ListBoxRow, self).__init__()
        grid = Gtk.Grid()
        self.add(grid)

        self.image = Gtk.Image()
        self.image.set_margin_top(5)
        self.image.set_margin_bottom(5)
        self.image.set_margin_left(5)
        self.image.set_margin_right(5)
        grid.attach(self.image, 0, 0, 5, 5)

        self.label1 = Gtk.Label()
        self.label1.set_margin_top(5)
        self.label1.set_alignment(0, 0.5)
        grid.attach(self.label1, 5, 0, 1, 1)

        self.selected = Gtk.CheckButton()
        grid.attach(self.selected, 5, 2, 1, 1)

        self.set_data(data)

    def set_selected(self, selected):
        self.selected = selected

    def set_data(self, data):
        self.data = data
        pixbuf = get_pixbuf_from_base64string(data['image']).scale_simple(
            64, 64, GdkPixbuf.InterpType.BILINEAR)
        self.image.set_from_pixbuf(pixbuf)
        if len(data['name']) > 50:
            name = data['name'][:47] + '...'
        else:
            name = data['name']
        self.label1.set_markup('<b>{0}</b>'.format(name))


class FoundPodcastsDDialog(Gtk.Dialog):
    """docstring for FoundPodcastsDDialog"""
    def __init__(self, window, data):
        Gtk.Dialog.__init__(self, '{0} | {1}'.format(comun.APPNAME,
                                                     _('Found podcasts')),
                            window,
                            Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT,
                             Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_default_size(600, 600)
        self.set_icon_from_file(comun.ICON)

        frame = Gtk.Frame()
        frame.set_margin_top(10)
        frame.set_margin_bottom(10)
        frame.set_margin_left(10)
        frame.set_margin_right(10)
        self.get_content_area().add(frame)
        vbox = Gtk.VBox(True, 10)
        frame.add(vbox)

        scrolledwindow = Gtk.ScrolledWindow()
        scrolledwindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                       Gtk.PolicyType.AUTOMATIC)
        scrolledwindow.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        scrolledwindow.set_size_request(300, 600)
        vbox.pack_start(scrolledwindow, True, True, 0)

        self.foundview = Gtk.ListBox()
        '''
        self.foundview.connect('row-activated', self.on_row_activated)
        self.foundview.connect('row-selected', self.on_row_selected)
        self.foundview.connect('selected-rows-changed',
                               self.on_row_selected_changed)
        '''
        self.foundview.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scrolledwindow.add(self.foundview)

        for afeed in data:
            row = PodcastFoundRow(afeed)
            row.show()
            self.foundview.add(row)

        self.show_all()

    def get_selecteds(self):
        selecteds = []
        for element in self.foundview.get_children():
            if element.selected.get_active() is True:
                selecteds.append(element.data)
        return selecteds


if __name__ == '__main__':
    from itunes import PodcastClient
    itp = PodcastClient()
    ans = itp.search('marketing', limit=20)
    if len(ans) > 0:
        fpd = FoundPodcastsDDialog(None, ans)
        if fpd.run() == Gtk.ResponseType.ACCEPT:
            print(fpd.get_selecteds())
        fpd.destroy()
