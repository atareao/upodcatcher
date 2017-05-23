#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# upodcatcher.py
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
    gi.require_version('Gdk', '3.0')
    gi.require_version('Gio', '2.0')
    gi.require_version('GLib', '2.0')
    gi.require_version('GObject', '2.0')
    gi.require_version('GdkPixbuf', '2.0')
except Exception as e:
    print(e)
    exit(1)
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import GdkPixbuf
import webbrowser
import os
import time
import base64
import requests
import comun
from comun import _
from dbmanager import DBManager
from player import Player
from downloader import Downloader
from sound_menu import SoundMenuControls
from dbus.mainloop.glib import DBusGMainLoop
from player import Status
from async import async_method
from addfeeddialog import AddFeedDialog


PLAY = GdkPixbuf.Pixbuf.new_from_file_at_size(comun.PLAY_ICON, 32, 32)
PAUSE = GdkPixbuf.Pixbuf.new_from_file_at_size(comun.PAUSE_ICON, 32, 32)
DOWNLOAD = GdkPixbuf.Pixbuf.new_from_file_at_size(comun.DOWNLOAD_ICON, 32, 32)
DOWNLOAD_ANIM = GdkPixbuf.PixbufAnimation.new_from_file(comun.DOWNLOAD_ANIM)
BACKWARD = GdkPixbuf.Pixbuf.new_from_file_at_size(comun.BACKWARD_ICON, 16, 16)
STEP_BACKWARD = GdkPixbuf.Pixbuf.new_from_file_at_size(
    comun.STEP_BACKWARD_ICON, 16, 16)
FORWARD = GdkPixbuf.Pixbuf.new_from_file_at_size(comun.FORWARD_ICON, 16, 16)
STEP_FORWARD = GdkPixbuf.Pixbuf.new_from_file_at_size(
    comun.STEP_FORWARD_ICON, 16, 16)
LPLAY = GdkPixbuf.Pixbuf.new_from_file_at_size(
    comun.LITTLE_PLAY_ICON, 16, 16)
LPAUSE = GdkPixbuf.Pixbuf.new_from_file_at_size(
    comun.LITTLE_PAUSE_ICON, 16, 16)


def select_value_in_combo(combo, value):
    model = combo.get_model()
    for i, item in enumerate(model):
        if value == item[0]:
            combo.set_active(i)
            return
    combo.set_active(0)


def get_selected_value_in_combo(combo):
    model = combo.get_model()
    return model.get_value(combo.get_active_iter(), 0)


def get_pixbuf_from_base64string(base64string):
    raw_data = base64.b64decode(base64string.encode())
    pixbuf_loader = GdkPixbuf.PixbufLoader.new_with_mime_type("image/png")
    pixbuf_loader.write(raw_data)
    pixbuf_loader.close()
    pixbuf = pixbuf_loader.get_pixbuf()
    return pixbuf


class ItemPodcast():
    def __init__(self, data, id):
        self.data = data
        self.id = id


class ListBoxRowWithData(Gtk.ListBoxRow):
    def __init__(self, data):
        super(Gtk.ListBoxRow, self).__init__()
        self.is_playing = False
        self.is_downloading = False
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

        self.label2 = Gtk.Label()
        self.label2.set_valign(Gtk.Align.FILL)
        self.label2.set_line_wrap(True)
        self.label2.set_alignment(0, 0.5)
        grid.attach(self.label2, 5, 1, 1, 2)

        self.label3 = Gtk.Label()
        self.label3.set_alignment(0, 0.5)
        grid.attach(self.label3, 5, 3, 1, 1)

        self.label4 = Gtk.Label()
        self.label4.set_alignment(0, 0.5)
        self.label4.set_margin_right(5)
        self.label4.set_halign(Gtk.Align.END)
        grid.attach(self.label4, 6, 3, 1, 1)

        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_margin_bottom(5)
        self.progressbar.set_valign(Gtk.Align.CENTER)
        self.progressbar.set_hexpand(True)
        self.progressbar.set_margin_right(5)
        grid.attach(self.progressbar, 5, 4, 2, 1)

        self.play_pause = Gtk.Image()
        self.play_pause.set_margin_top(5)
        self.play_pause.set_margin_bottom(5)
        self.play_pause.set_margin_left(5)
        self.play_pause.set_margin_right(5)
        grid.attach(self.play_pause, 8, 0, 5, 5)

        self.set_data(data)

    def set_downloading(self, downloading):
        self.is_downloading = downloading
        if downloading is True:
            self.play_pause.set_from_animation(DOWNLOAD_ANIM)
        else:
            if self.data['filename'] is None:
                self.play_pause.set_from_pixbuf(DOWNLOAD)
            else:
                if os.path.exists(os.path.join(
                        comun.PODCASTS_DIR, self.data['filename'])):
                    self.play_pause.set_from_pixbuf(PLAY)
                else:
                    self.play_pause.set_from_pixbuf(DOWNLOAD)

    def set_playing(self, playing):
        self.is_playing = playing
        if playing is True:
            self.play_pause.set_from_pixbuf(PAUSE)
        else:
            self.play_pause.set_from_pixbuf(PLAY)

    def __eq__(self, other):
        return self.data['id'] == other.data['id']

    def set_duration(self, duration):
        self.data['duration'] = duration
        self.label4.set_text(time.strftime('%H:%M:%S', time.gmtime(
            self.data['duration'])))

    def get_duration(self):
        return self.data['duration']

    def get_position(self):
        return self.data['position']

    def set_position(self, position):
        self.data['position'] = position
        self.label3.set_text(time.strftime('%H:%M:%S', time.gmtime(
            self.data['position'])))
        if self.data['duration'] > 0:
            fraction = float(position) / float(self.data['duration'])
            self.progressbar.set_fraction(fraction)

    def set_data(self, data):
        self.data = data
        pixbuf = get_pixbuf_from_base64string(data['feed_image']).scale_simple(
            64, 64, GdkPixbuf.InterpType.BILINEAR)
        self.image.set_from_pixbuf(pixbuf)
        self.label1.set_markup(
            '<big><b>{0}</b></big>'.format(data['feed_name']))
        self.label2.set_text(data['title'])
        self.set_duration(data['duration'])
        self.set_position(data['position'])
        self.set_downloading(False)


class MainApplication(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(
            self,
            application_id='es.atareao.upodcatcher',
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.license_type = Gtk.License.GPL_3_0

    def do_shutdown(self):
        Gtk.Application.do_shutdown(self)

    def on_quit(self, widget, data):
        self.quit()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        def create_action(name,
                          callback=self.action_clicked,
                          var_type=None,
                          value=None):
            if var_type is None:
                action = Gio.SimpleAction.new(name, None)
            else:
                action = Gio.SimpleAction.new_stateful(
                    name,
                    GLib.VariantType.new(var_type),
                    GLib.Variant(var_type, value)
                )
            action.connect('activate', callback)
            return action

        self.add_action(create_action("quit", callback=lambda *_: self.quit()))

        self.set_accels_for_action('app.add', ['<Ctrl>A'])
        self.set_accels_for_action('app.open', ['<Ctrl>O'])
        self.set_accels_for_action('app.quit', ['<Ctrl>Q'])
        self.set_accels_for_action('app.about', ['<Ctrl>F'])

        self.add_action(create_action(
            'new',
            callback=self.on_headbar_clicked))
        self.add_action(create_action(
            'open',
            callback=self.on_headbar_clicked))
        self.add_action(create_action(
            'close',
            callback=self.on_headbar_clicked))
        self.add_action(create_action(
            'save',
            callback=self.on_headbar_clicked))
        self.add_action(create_action(
            'save_as',
            callback=self.on_headbar_clicked))

        self.add_action(create_action(
            'set_preferences',
            callback=self.on_preferences_clicked))
        self.add_action(create_action(
            'goto_homepage',
            callback=lambda x, y: webbrowser.open(
                'http://www.atareao.es/apps/\
crear-un-gif-animado-de-un-video-en-ubuntu-en-un-solo-clic/')))
        self.add_action(create_action(
            'goto_bug',
            callback=lambda x, y: webbrowser.open(
                'https://bugs.launchpad.net/2gif')))
        self.add_action(create_action(
            'goto_sugestion',
            callback=lambda x, y: webbrowser.open(
                'https://blueprints.launchpad.net/2gif')))
        self.add_action(create_action(
            'goto_translation',
            callback=lambda x, y: webbrowser.open(
                'https://translations.launchpad.net/2gif')))
        self.add_action(create_action(
            'goto_questions',
            callback=lambda x, y: webbrowser.open(
                'https://answers.launchpad.net/2gif')))
        self.add_action(create_action(
            'goto_twitter',
            callback=lambda x, y: webbrowser.open(
                'https://twitter.com/atareao')))
        self.add_action(create_action(
            'goto_google_plus',
            callback=lambda x, y: webbrowser.open(
                'https://plus.google.com/\
118214486317320563625/posts')))
        self.add_action(create_action(
            'goto_facebook',
            callback=lambda x, y: webbrowser.open(
                'http://www.facebook.com/elatareao')))
        self.add_action(create_action(
            'goto_donate',
            callback=self.on_support_clicked))
        self.add_action(create_action(
            'about',
            callback=self.on_about_activate))
        self.add_action(create_action(
            'none',
            callback=self.do_none))
        action_toggle = Gio.SimpleAction.new_stateful(
            "toggle", None, GLib.Variant.new_boolean(False))
        action_toggle.connect("change-state", self.toggle_toggled)
        self.add_action(action_toggle)

        lbl_variant = GLib.Variant.new_string("h3")
        new_action = Gio.SimpleAction.new_stateful("new",
                                                   lbl_variant.get_type(),
                                                   lbl_variant)
        new_action.connect("activate", self.activate_radio)
        new_action.connect("change-state", self.toggle_heading)
        self.add_action(new_action)

        action_heading = Gio.SimpleAction.new_stateful(
            "heading",
            GLib.VariantType.new("s"),
            GLib.Variant("s", "h1"))
        action_heading.connect("activate", self.activate_radio)
        action_heading.connect("change-state", self.toggle_heading)
        self.add_action(action_heading)

    def activate_radio(self, widget, action, parameter=None):
        self.win.menu['lists'].set_label(action.get_string())
        widget.set_state(action)

    def heading(self, action):
        print(action)

    def toggle_heading(self, action, state):
        print(action, state)

    def do_activate(self):
        self.win = MainWindow(self)
        self.add_window(self.win)
        self.win.show()

    def action_clicked(self, action, variant):
        print(action, variant)
        if variant:
            action.set_state(variant)

    def on_headbar_clicked(self, action, optional):
        self.win.on_toolbar_clicked(action, action.get_name())

    def on_preferences_clicked(self, widget, optional):
        pass
        '''
        cm = PreferencesDialog(self.win)
        if cm.run() == Gtk.ResponseType.ACCEPT:
            cm.close_ok()
        cm.destroy()
        '''

    def on_support_clicked(self, widget, optional):
        pass
        '''
        dialog = SupportDialog(self.win)
        dialog.run()
        dialog.destroy()
        '''

    def on_about_activate(self, widget, optional):
        ad = Gtk.AboutDialog()
        ad.set_name(comun.APPNAME)
        ad.set_version(comun.VERSION)
        ad.set_copyright('Copyrignt (c) 2011-2016\nLorenzo Carbonell')
        ad.set_comments(_('An application to work with markdown'))
        ad.set_license('''
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
''')
        ad.set_website('http://www.atareao.es')
        ad.set_website_label('http://www.atareao.es')
        ad.set_authors([
            'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
        ad.set_documenters([
            'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
        ad.set_translator_credits('\
Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>\n')
        ad.set_program_name('uText')
        ad.set_logo(GdkPixbuf.Pixbuf.new_from_file(comun.ICON))
        ad.run()
        ad.destroy()

    def do_none(self, *args):
        pass

    def toggle_toggled(self, action, state):
            action.set_state(state)
            Gtk.Settings.get_default().set_property(
                "gtk-application-prefer-dark-theme", state)


def get_thumbnail_filename_for_feed(feed_id, base64string):
    thumbnail_filename = os.path.join(comun.THUMBNAILS_DIR,
                                      'feed_{0}.png'.format(feed_id))
    if not os.path.exists(thumbnail_filename):
        pixbuf = get_pixbuf_from_base64string(base64string)
        pixbuf.savev(thumbnail_filename, 'png', [], [])
    return thumbnail_filename


class MainWindow(Gtk.ApplicationWindow):
    __gsignals__ = {
        'text-changed': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,
                         (object,)),
        'save-me': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,
                    (object,)), }

    def __init__(self, app, afile=None):
        Gtk.ApplicationWindow.__init__(self, application=app)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_icon_from_file(comun.ICON)
        self.set_default_size(600, 600)
        # self.builder = Gtk.Builder()
        # self.builder.add_from_file(comun.UI_FILE)
        # self.connect('delete-event', self.on_close_application)
        # self.connect('realize', self.on_activate_preview_or_html)
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        # Vertical box. Contains menu and PaneView
        vbox = Gtk.VBox(False, 2)
        self.current_row = None
        self.object = None

        self.player = Player()
        self.player.connect('started', self.on_player_started)
        self.player.connect('paused', self.on_player_paused)
        self.player.connect('stopped', self.on_player_stopped)

        DBusGMainLoop(set_as_default=True)
        self.sound_menu = SoundMenuControls('uPodcatcher')
        self.sound_menu._sound_menu_is_playing = self._sound_menu_is_playing
        self.sound_menu._sound_menu_play = self._sound_menu_play
        self.sound_menu._sound_menu_pause = self._sound_menu_pause
        self.sound_menu._sound_menu_next = self._sound_menu_next
        self.sound_menu._sound_menu_previous = self._sound_menu_previous
        self.sound_menu._sound_menu_raise = self._sound_menu_raise
        self.sound_menu._sound_menu_stop = self._sound_menu_stop

        self.add(vbox)
        #

        # Init HeaderBar
        self.init_headerbar()

        # Init Menu
        # self.init_menu()

        # Init Toolbar
        # self.init_toolbar()
        #
        self.scrolledwindow1 = Gtk.ScrolledWindow()
        self.scrolledwindow1.set_policy(Gtk.PolicyType.AUTOMATIC,
                                  Gtk.PolicyType.AUTOMATIC)
        self.scrolledwindow1.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        self.scrolledwindow1.set_visible(True)
        vbox.pack_start(self.scrolledwindow1, True, True, 0)

        self.scrolledwindow2 = Gtk.ScrolledWindow()
        self.scrolledwindow2.set_policy(Gtk.PolicyType.AUTOMATIC,
                                  Gtk.PolicyType.AUTOMATIC)
        self.scrolledwindow2.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        vbox.pack_start(self.scrolledwindow2, True, True, 0)
        self.scrolledwindow2.set_visible(False)

        self.storefeeds = Gtk.ListStore(int,
                                        str,
                                        str,
                                        str,
                                        int,
                                        GdkPixbuf.Pixbuf)

        self.storetracks = Gtk.ListStore(int,
                                         str,
                                         str,
                                         str,
                                         str,
                                         str,
                                         str,
                                         bool,
                                         bool,
                                         int,
                                         GdkPixbuf.Pixbuf)
        self.iconview = Gtk.IconView()
        self.iconview.set_model(self.storefeeds)
        self.iconview.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.iconview.set_pixbuf_column(5)
        self.iconview.set_text_column(2)
        self.iconview.set_item_width(128)
        self.iconview.set_columns(-1)
        self.iconview.set_column_spacing(0)
        self.iconview.set_spacing(0)
        self.iconview.set_row_spacing(20)
        self.iconview.set_item_padding(0)
        self.iconview.connect('item-activated',
                              self.on_iconview_actived)
        self.scrolledwindow1.add(self.iconview)

        self.trackview = Gtk.ListBox()
        self.trackview.connect('row-activated', self.on_row_activated)
        self.trackview.connect('row-selected', self.on_row_selected)
        self.trackview.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.scrolledwindow2.add(self.trackview)


        # StatusBar
        self.statusbar = Gtk.Statusbar()

        speed_store = Gtk.ListStore(float, str)
        speed_store.append([0.5, '0.5x'])
        speed_store.append([0.6, '0.6x'])
        speed_store.append([0.7, '0.7x'])
        speed_store.append([0.8, '0.8x'])
        speed_store.append([0.9, '0.9x'])
        speed_store.append([1.0, '1.0x'])
        speed_store.append([1.1, '1.1x'])
        speed_store.append([1.2, '1.2x'])
        speed_store.append([1.3, '1.3x'])
        speed_store.append([1.4, '1.4x'])
        speed_store.append([1.5, '1.5x'])
        speed_store.append([1.6, '1.6x'])
        speed_store.append([1.7, '1.7x'])
        speed_store.append([1.8, '1.8x'])
        speed_store.append([1.9, '1.9x'])
        speed_store.append([2.0, '2.0x'])
        self.combo_speed = Gtk.ComboBox.new_with_model(speed_store)
        cell1 = Gtk.CellRendererText()
        self.combo_speed.pack_start(cell1, True)
        self.combo_speed.add_attribute(cell1, 'text', 1)
        self.combo_speed.set_active(5)
        self.combo_speed.connect('changed', self.on_combo_speed_changed)

        self.statusbar.pack_start(self.combo_speed, False, False, 0)
        self.btn_step_backward = Gtk.Button.new()
        self.btn_step_backward.add(Gtk.Image.new_from_pixbuf(STEP_BACKWARD))
        self.btn_step_backward.connect('clicked', self._sound_menu_previous)
        self.statusbar.pack_start(self.btn_step_backward, False, False, 0)
        self.btn_backward = Gtk.Button.new()
        self.btn_backward.add(Gtk.Image.new_from_pixbuf(BACKWARD))
        self.btn_backward.connect('clicked', self.on_backward_clicked)
        self.statusbar.pack_start(self.btn_backward, False, False, 0)
        self.btn_play_pause = Gtk.Button.new()
        self.img_play_pause = Gtk.Image.new_from_pixbuf(LPLAY)
        self.btn_play_pause.add(self.img_play_pause)
        self.btn_play_pause.connect('clicked', self._sound_menu_play)
        self.statusbar.pack_start(self.btn_play_pause, False, False, 0)
        self.btn_forward = Gtk.Button.new()
        self.btn_forward.add(Gtk.Image.new_from_pixbuf(FORWARD))
        self.btn_forward.connect('clicked', self.on_forward_clicked)
        self.statusbar.pack_start(self.btn_forward, False, False, 0)
        self.btn_step_forward = Gtk.Button.new()
        self.btn_step_forward.add(Gtk.Image.new_from_pixbuf(STEP_FORWARD))
        self.btn_step_forward.connect('clicked', self._sound_menu_next)
        self.statusbar.pack_start(self.btn_step_forward, False, False, 0)
        self.statusbar.set_sensitive(False)

        vbox.pack_start(self.statusbar, False, False, 0)
        #
        self.db = DBManager(False)
        for feed in self.db.get_feeds():
            thumbnail = os.path.join(comun.THUMBNAILS_DIR,
                                     'feed_{0}.png'.format(feed['id']))
            pixbuf = get_pixbuf_from_base64string(feed['image'])
            if not os.path.exists(thumbnail):
                pixbuf.savev(thumbnail, 'png', [], [])

            self.storefeeds.append([feed['id'],
                                    feed['url'],
                                    feed['title'],
                                    feed['image'],
                                    feed['norder'],
                                    pixbuf])
        self.show_all()

    def on_iconview_actived(self, widget, index):
        print(widget, index)
        model = widget.get_model()
        selected = widget.get_selected_items()[0]
        id = model.get_value(model.get_iter(selected), 0)

        self.object = self.db.get_feed(id)

        self.menu['back'].get_child().set_from_gicon(Gio.ThemedIcon(
            name='media-playback-start-rtl-symbolic'), Gtk.IconSize.BUTTON)
        self.menu['back'].connect('clicked', self.on_button_back_clicked)
        self.menu['back'].set_sensitive(True)

        url = model.get_value(model.get_iter(selected), 1)
        print(id, url)
        for awidget in self.trackview.get_children():
            self.trackview.remove(awidget)
        self.db.add_tracks(id)
        for index, track in enumerate(self.db.get_tracks_from_feed(id)):
            print('---', index, '---')
            row = ListBoxRowWithData(track)
            row.show()
            self.trackview.add(row)
        widget.hide()
        self.scrolledwindow1.set_visible(False)
        self.scrolledwindow2.set_visible(True)
        self.scrolledwindow2.show_all()
        self.statusbar.set_sensitive(True)

    def on_button_back_clicked(self, widget):
        self.scrolledwindow2.set_visible(False)
        self.statusbar.set_sensitive(False)
        self.scrolledwindow1.show_all()
        self.scrolledwindow1.set_visible(True)
        self.object = None

    def on_combo_speed_changed(self, combo):
        value = get_selected_value_in_combo(combo)
        self.player.set_speed(value)

    def _sound_menu_is_playing(self):
        return self.player.status == Status.PLAYING

    def _sound_menu_play(self, *args):
        """Play"""
        # self.is_playing = True  # Need to overwrite
        if self.current_row is None:
            self.current_row = self.trackview.get_row_at_index(0)
            self.trackview.select_row(self.current_row)
        self.on_row_activated(None, self.current_row)

    def _sound_menu_stop(self):
        """Pause"""
        if self.current_row is not None:
            self.on_row_activated(None, self.current_row)

    def _sound_menu_pause(self, *args):
        """Pause"""
        if self.current_row is not None:
            self.on_row_activated(None, self.current_row)

    def _sound_menu_next(self, *args):
        """Next"""
        index = self.current_row.get_index()
        index += 1
        if index > len(self.trackview.get_children()) - 1:
            index = 0
        row = self.trackview.get_row_at_index(index)
        self.trackview.select_row(row)
        self.on_row_activated(None, row)

    def _sound_menu_previous(self, *args):
        """Previous"""
        index = self.current_row.get_index()
        index -= 1
        if index < 0:
            index = len(self.trackview.get_children()) - 1
        row = self.trackview.get_row_at_index(index)
        self.trackview.select_row(row)
        self.on_row_activated(None, row)

    def _sound_menu_raise(self):
        """Click on player"""
        self.win_preferences.show()

    def on_row_selected(self, widget, row):
        #self.previous_row = self.current_row
        #self.current_row = row
        print('-------- selected ----------')
        if row.data['filename'] is None or not os.path.exists(os.path.join(
                comun.PODCASTS_DIR, row.data['filename'])):
            self.btn_play_pause.set_sensitive(False)
            self.btn_forward.set_sensitive(False)
            self.btn_backward.set_sensitive(False)
            self.combo_speed.set_sensitive(False)
        else:
            self.btn_play_pause.set_sensitive(True)
            self.btn_forward.set_sensitive(True)
            self.btn_backward.set_sensitive(True)
            self.combo_speed.set_sensitive(True)

    def update_duration(self):
        duration = self.player.get_duration()
        self.db.set_track_duration(self.current_row.data['id'], duration)
        self.current_row.set_duration(duration)
        return False

    def update_position(self):
        position = self.player.get_position()
        self.current_row.set_position(position)
        return self.player.status == Status.PLAYING

    def on_player_started(self, player, position):
        print('**** player started ****')
        self.img_play_pause.set_from_pixbuf(LPAUSE)
        self.current_row.set_playing(True)
        if self.current_row.data['position'] > 0:
            self.player.set_position(self.current_row.data['position'])
        if self.current_row.data['duration'] == 0:
            GLib.timeout_add(50, self.update_duration)
        GLib.timeout_add_seconds(1, self.update_position)
        artists = [self.current_row.data['feed_name']]
        album = self.current_row.data['feed_name']
        title = self.current_row.data['title']
        feed_id = self.current_row.data['feed_id']
        feed_image = self.current_row.data['feed_image']
        album_art = get_thumbnail_filename_for_feed(feed_id, feed_image)
        self.sound_menu.song_changed(artists, album, title, album_art)
        self.sound_menu.signal_playing()

    def on_player_paused(self, player, position):
        print('**** player paused ****')
        self.current_row.set_playing(False)
        self.img_play_pause.set_from_pixbuf(LPLAY)
        position = self.player.get_position()
        self.db.set_track_position(self.current_row.data['id'], position)
        self.current_row.set_position(position)
        artists = [self.current_row.data['feed_name']]
        album = self.current_row.data['feed_name']
        title = self.current_row.data['title']
        feed_id = self.current_row.data['feed_id']
        feed_image = self.current_row.data['feed_image']
        album_art = get_thumbnail_filename_for_feed(feed_id, feed_image)
        self.sound_menu.song_changed(artists, album, title, album_art)
        self.sound_menu.signal_paused()

    def on_player_stopped(self, player, position):
        pass

    def on_row_activated(self, widget, row):
        if row != self.trackview.get_selected_row():
            self.trackview.select_row(row)

        if self.current_row is None or self.current_row != row:
            if self.current_row is not None:
                self.current_row.set_playing(False)
            self.current_row = row
            self.player.stop()

        if row.data['filename'] is not None and os.path.exists(os.path.join(
                comun.PODCASTS_DIR, row.data['filename'])):
            if self.current_row.is_playing:
                self.player.pause()
            else:
                self.player.set_filename(os.path.join(comun.PODCASTS_DIR,
                                                      row.data['filename']))
                value = get_selected_value_in_combo(self.combo_speed)
                self.player.set_speed(value)
                self.player.play()
        else:
            url = row.data['url']
            ext = url.split('.')[-1]
            filename = os.path.join(comun.PODCASTS_DIR,
                                    'podcast_{0}.{1}'.format(row.data['id'],
                                                             ext))
            if row.is_downloading is False:
                downloader = Downloader(url, filename)
                downloader.connect('ended', self.on_downloader_ended,
                                   row, filename)
                downloader.connect('failed', self.on_downloader_failed,
                                   row, filename)
                downloader.start()
                row.set_downloading(True)

    def on_downloader_failed(self, widget, row, filename):
        if os.path.exists(filename):
            os.remove(filename)
        row.set_downloading(False)

    def on_downloader_ended(self, widget, row, filename):
        self.db.set_track_downloaded(row.data['id'], filename.split('/')[-1])
        ans = self.db.get_track_from_feed(row.data['id'])
        if ans is not None:
            row.set_data(ans)
        row.set_downloading(False)
        if self.trackview.get_selected_row() == row:
            self.btn_play_pause.set_sensitive(True)
            self.btn_forward.set_sensitive(True)
            self.btn_backward.set_sensitive(True)
            self.combo_speed.set_sensitive(True)
        self.on_row_activated(None, row)

    def on_forward_clicked(self, widget):
        if self.current_row is not None:
            position = self.current_row.get_position()
            position += 30
            if position > self.current_row.get_duration():
                self.position = 0
            self.current_row.set_position(position)
            self.player.set_position(position)

    def on_backward_clicked(self, widget):
        if self.current_row is not None:
            position = self.current_row.get_position()
            position -= 30
            if position < 0:
                position = 0
            self.current_row.set_position(position)
            self.player.set_position(position)

    def init_headerbar(self):
        icontheme = Gtk.IconTheme.get_default()
        self.menu = {}
        self.menu_selected = 'suscriptions'
        #
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = comun.APPNAME
        self.set_titlebar(hb)

        self.menu['suscriptions'] = Gtk.ToggleButton.new_with_label(_(
            'Suscriptions'))
        self.menu['suscriptions'].set_active(True)
        self.menu['suscriptions'].connect('toggled', self.on_toggled, 'suscriptions')
        hb.pack_start(self.menu['suscriptions'])

        # menumodel = self.builder.get_object("heading-menu")
        menumodel = Gio.Menu()
        item = Gio.MenuItem.new('Lista 1', 'app.heading')
        item.set_attribute_value('target', GLib.Variant.new_string('Lista 1'))
        menumodel.append_item(item)
        item = Gio.MenuItem.new('Lista 2', 'app.heading')
        item.set_attribute_value('target', GLib.Variant.new_string('Lista 2'))
        menumodel.append_item(item)
        item = Gio.MenuItem.new('Lista 3', 'app.heading')
        item.set_attribute_value('target', GLib.Variant.new_string('Lista 3'))
        menumodel.append_item(item)


        self.menu['lists'] = Gtk.MenuButton(_('Lists'))
        self.menu['lists'].connect('toggled', self.on_toggled, 'lists')
        self.menu['lists'].set_menu_model(menumodel)
        hb.pack_start(self.menu['lists'])

        self.menu['remove'] = Gtk.Button()
        self.menu['remove'].add(Gtk.Image.new_from_gicon(Gio.ThemedIcon(
            name='list-remove-symbolic'), Gtk.IconSize.BUTTON))
        hb.pack_end(self.menu['remove'])

        self.menu['add'] = Gtk.Button()
        self.menu['add'].add(Gtk.Image.new_from_gicon(Gio.ThemedIcon(
            name='list-add-symbolic'), Gtk.IconSize.BUTTON))
        self.menu['add'].connect('clicked', self.on_add_feed_clicked)
        hb.pack_end(self.menu['add'])

        self.menu['back'] = Gtk.Button()
        self.menu['back'].add(Gtk.Image.new_from_gicon(Gio.ThemedIcon(
            name='media-record-symbolic'), Gtk.IconSize.BUTTON))
        hb.pack_end(self.menu['back'])

    def on_add_feed_clicked(self, widget):
        if self.object is None:
            afd = AddFeedDialog()
            if afd.run() == Gtk.ResponseType.ACCEPT:
                url = afd.get_url()
                if not url.startswith('http://') or url.startswith('https://'):
                    url = 'http://' + url
                    self.add_feed(url)
            afd.destroy()

    def on_toolbar_clicked(self, widget, option):
        print(widget, option)

    @async_method
    def add_feed(self, url):
        print(url)
        request = requests.get(url)
        if request.status_code == 200:
            id = self.db. add_feed(url)
            if id is not None:
                print(id)
                feed = self.db.get_feed(id)
                print(feed)
                thumbnail = os.path.join(comun.THUMBNAILS_DIR,
                                         'feed_{0}.png'.format(feed['id']))
                pixbuf = get_pixbuf_from_base64string(feed['image'])
                if not os.path.exists(thumbnail):
                    pixbuf.savev(thumbnail, 'png', [], [])
                self.storefeeds.append([feed['id'],
                                        feed['url'],
                                        feed['title'],
                                        feed['image'],
                                        feed['norder'],
                                        pixbuf])

    def on_toggled(self, widget, arg):
        if widget.get_active() is True:
            if arg == self.menu_selected:
                if self.menu[arg].get_active() is False:
                    self.menu[arg].set_active(True)
            else:
                old = self.menu_selected
                self.menu_selected = arg
                self.menu[old].set_active(False)
        else:
            if self.menu_selected == arg:
                widget.set_active(True)
        print(arg, self.menu[arg].get_active())


def main():
    app = MainApplication()
    app.run('')


if __name__ == "__main__":
    main()
