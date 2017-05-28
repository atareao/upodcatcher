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
    gi.require_version('Notify', '0.7')
except Exception as e:
    print(e)
    exit(1)
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import GdkPixbuf
from gi.repository import Notify
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
NOIMAGE = GdkPixbuf.Pixbuf.new_from_file_at_size(comun.NOIMAGE_ICON, 128, 128)
LISTENED = GdkPixbuf.Pixbuf.new_from_file_at_size(
    comun.LISTENED_ICON, 16, 16)
NOLISTENED = GdkPixbuf.Pixbuf.new_from_file_at_size(
    comun.NOLISTENED_ICON, 16, 16)


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
    if base64string is None:
        return NOIMAGE
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

        self.listened = Gtk.Image()
        self.listened.set_from_pixbuf(NOLISTENED)
        self.listened.set_margin_top(5)
        self.listened.set_margin_bottom(5)
        self.listened.set_margin_left(5)
        self.listened.set_margin_right(5)
        grid.attach(self.listened, 7, 0, 1, 1)

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
            if self.data['downloaded'] == 0:
                self.play_pause.set_from_pixbuf(DOWNLOAD)
            else:
                self.play_pause.set_from_pixbuf(PLAY)

    def set_downloaded(self, downloaded):
        if downloaded is True:
            self.data['downloaded'] = 1
            self.play_pause.set_from_pixbuf(PLAY)
        else:
            self.data['downloaded'] = 0
            self.play_pause.set_from_pixbuf(DOWNLOAD)

    def set_playing(self, playing):
        self.is_playing = playing
        if self.data['downloaded'] == 1:
            if playing is True:
                self.play_pause.set_from_pixbuf(PAUSE)
            else:
                self.play_pause.set_from_pixbuf(PLAY)
        elif self.is_downloading:
            self.play_pause.set_from_animation(DOWNLOAD_ANIM)
        else:
            self.play_pause.set_from_pixbuf(DOWNLOAD)

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

    def set_listened(self, listened):
        self.data['listened'] = 1 if listened is True else 0
        if listened is True:
            self.listened.set_from_pixbuf(LISTENED)
        else:
            self.listened.set_from_pixbuf(NOLISTENED)

    def set_position(self, position):
        self.data['position'] = position
        self.label3.set_text(time.strftime('%H:%M:%S', time.gmtime(
            self.data['position'])))
        if self.data['duration'] > 0:
            fraction = float(position) / float(self.data['duration'])
            self.progressbar.set_fraction(fraction)

    def set_filename(self, filename):
        self.data['filename'] = filename

    def set_data(self, data):
        print('============================')
        # print(data)
        print(data['id'], 'listened', data['listened'], type(data['listened']))
        print('============================')
        self.data = data
        pixbuf = get_pixbuf_from_base64string(data['feed_image']).scale_simple(
            64, 64, GdkPixbuf.InterpType.BILINEAR)
        self.image.set_from_pixbuf(pixbuf)
        self.label1.set_markup(
            '<big><b>{0}</b></big>'.format(data['feed_name']))
        self.label2.set_text(data['title'])
        if data['listened'] == 1:
            self.listened.set_from_pixbuf(LISTENED)
        else:
            self.listened.set_from_pixbuf(NOLISTENED)
        if data['downloaded'] == 1:
            self.play_pause.set_from_pixbuf(PLAY)
        else:
            self.play_pause.set_from_pixbuf(DOWNLOAD)
        self.set_duration(data['duration'])
        self.set_position(data['position'])
        self.is_playing = False
        self.is_downloading = False


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
                'http://www.atareao.es/')))
        self.add_action(create_action(
            'goto_code',
            callback=lambda x, y: webbrowser.open(
                'https://github.com/atareao/upodcatcher')))
        self.add_action(create_action(
            'goto_bug',
            callback=lambda x, y: webbrowser.open(
                'https://github.com/atareao/upodcatcher/issues')))
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
        ad = Gtk.AboutDialog(comun.APPNAME, self.win)
        ad.set_name(comun.APPNAME)
        ad.set_version(comun.VERSION)
        ad.set_copyright('Copyrignt (c) 2017\nLorenzo Carbonell')
        ad.set_comments(_('A manager for podcasts'))
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
        ad.set_program_name(comun.APPNAME)
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
        '''
        dbus.set_default_main_loop(dbus.mainloop.glib.DBusGMainLoop())
        bus = dbus.SessionBus()
        if bus.request_name('es.atareao.upodcatcher') !=\
                dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER:
            print("application already running")
            #exit(0)
        '''

        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_icon_from_file(comun.ICON)
        self.set_default_size(600, 600)
        # self.builder = Gtk.Builder()
        # self.builder.add_from_file(comun.UI_FILE)
        # self.connect('delete-event', self.on_close_application)
        # self.connect('realize', self.on_activate_preview_or_html)

        max_action = Gio.SimpleAction.new_stateful(
            "maximize", None, GLib.Variant.new_boolean(False))
        max_action.connect("change-state", self.on_maximize_toggle)
        self.add_action(max_action)

        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.notification = Notify.Notification.new('', '', None)
        # Vertical box. Contains menu and PaneView
        vbox = Gtk.VBox(False, 2)
        self.object = None
        self.active_row = None

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

        self.iconview = Gtk.IconView()
        self.iconview.set_model(self.storefeeds)
        self.iconview.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.iconview.set_pixbuf_column(5)
        self.iconview.set_text_column(2)
        self.iconview.set_item_width(90)
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
        self.trackview.connect('selected-rows-changed',
                               self.on_row_selected_changed)
        # self.trackview.set_activate_on_single_click(False)
        self.trackview.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.scrolledwindow2.add(self.trackview)

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
        self.scrolledwindow2.set_visible(False)
        self.play_controls.set_visible(False)
        self.feed_controls.set_visible(True)

    def on_equalizer_value_changed(self, widget, value):
        print(widget, type(widget), value)
        widget.set_label('{0}\n17Hz'.format(int(value)))

    def on_maximize_toggle(self, action, value):
            action.set_state(value)
            if value.get_boolean():
                self.maximize()
            else:
                self.unmaximize()

    def on_iconview_actived(self, widget, index):
        print(widget, index)
        model = widget.get_model()
        selected = widget.get_selected_items()[0]
        id = model.get_value(model.get_iter(selected), 0)

        self.object = self.db.get_feed(id)

        url = model.get_value(model.get_iter(selected), 1)
        print(id, url)
        for awidget in self.trackview.get_children():
            self.trackview.remove(awidget)
        # self.db.add_tracks(id)
        for index, track in enumerate(self.db.get_tracks_from_feed(id)):
            print('---', index, '---')
            row = ListBoxRowWithData(track)
            row.show()
            self.trackview.add(row)
        widget.hide()

        self.get_root_window().set_cursor(
            Gdk.Cursor(Gdk.CursorType.WATCH))

        self.update_tracks(id)
        self.scrolledwindow1.set_visible(False)
        self.scrolledwindow2.set_visible(True)
        self.scrolledwindow2.show_all()
        self.play_controls.set_visible(True)
        self.feed_controls.set_visible(False)
        row = self.trackview.get_row_at_index(0)
        self.trackview.select_row(row)

    @async_method(on_done=lambda self, result, error:
                  self.on_update_tracks_done(result, error))
    def update_tracks(self, id):
        result = None
        print('update_tracks', id)
        last_track = self.db.get_last_track_from_feed(id)
        last_feed_track = self.db.get_last_track_date(id)
        print(1, last_track['date'], last_feed_track)
        if last_track['date'] is None or last_feed_track > last_track['date']:
            self.db.add_tracks(id, last_track['date'])
            result = (id, last_track['date'])
            print('result', result)
        print('---', last_track['date'], last_feed_track, '---')
        return result

    def on_update_tracks_done(self, result, error):
        print(1, error, result)
        if error is None and result is not None:
            tracks = self.db.get_tracks_from_feed(*result)
            for index, track in enumerate(tracks):
                print('---', index, '---')
                row = ListBoxRowWithData(track)
                row.show()
                self.trackview.add(row)
            self.scrolledwindow2.set_visible(True)
            self.scrolledwindow2.show_all()
        self.get_root_window().set_cursor(
            Gdk.Cursor(Gdk.CursorType.TOP_LEFT_ARROW))

    def on_button_up_clicked(self, widget):
        if self.player is not None:
            self.player.pause()
        self.scrolledwindow2.set_visible(False)
        self.scrolledwindow1.show_all()
        self.scrolledwindow1.set_visible(True)
        self.play_controls.set_visible(False)
        self.feed_controls.set_visible(True)
        self.object = None

    def on_combo_speed_changed(self, combo):
        value = get_selected_value_in_combo(combo)
        self.player.set_speed(value)

    def _sound_menu_is_playing(self):
        return self.player.status == Status.PLAYING

    def _sound_menu_play(self, *args):
        """Play"""
        # self.is_playing = True  # Need to overwrite
        row = self.trackview.get_selected_row()
        if row is None:
            row = self.trackview.get_row_at_index(0)
            self.trackview.select_row(row)
        self.on_row_activated(None, row)

    def _sound_menu_stop(self):
        """Pause"""
        if self.trackview.get_selected_row() is not None:
            self.on_row_activated(None, self.trackview.get_selected_row())

    def _sound_menu_pause(self, *args):
        """Pause"""
        if self.trackview.get_selected_row() is not None:
            self.on_row_activated(None, self.self.trackview.get_selected_row())

    def _sound_menu_next(self, *args):
        """Next"""
        index = self.trackview.get_selected_row().get_index()
        index += 1
        if index > len(self.trackview.get_children()) - 1:
            index = 0
        row = self.trackview.get_row_at_index(index)
        self.trackview.select_row(row)
        self.on_row_activated(None, row)

    def _sound_menu_previous(self, *args):
        """Previous"""
        index = self.trackview.get_selected_row().get_index()
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
        print('-------- selected ----------', row.data['id'],
              self.trackview.get_selected_row().data['id'])
        if row is not None and row.data['downloaded'] == 0:
            self.control['play-pause'].set_sensitive(False)
            self.control['speed'].set_sensitive(False)
            self.control['position'].set_sensitive(False)
        else:
            self.control['play-pause'].set_sensitive(True)
            self.control['speed'].set_sensitive(True)
            self.control['position'].set_sensitive(True)
        self.on_row_activated(widget, row)

    def update_duration(self):
        if self.trackview.get_selected_row() is not None:
            duration = self.player.get_duration()
            self.db.set_track_duration(
                self.trackview.get_selected_row().data['id'], duration)
            self.trackview.get_selected_row().set_duration(duration)
        return False

    def update_position(self):
        if self.trackview.get_selected_row() is not None:
            position = self.player.get_position()
            duration = self.trackview.get_selected_row().data['duration']
            if duration > 0:
                fraction = float(position) / float(duration)
                if fraction > 0.95:
                    self.db.set_track_listened(
                        self.trackview.get_selected_row().data['id'])
                    self.trackview.get_selected_row().set_listened(True)
                self.trackview.get_selected_row().set_position(position)

                self.control['position'].handler_block_by_func(
                    self.on_position_button_changed)
                self.control['position'].set_value(int(fraction * 100))
                self.control['position'].set_label('{0}%'.format(
                    int(fraction * 100)))
                self.control['position'].handler_unblock_by_func(
                    self.on_position_button_changed)

            return self.player.status == Status.PLAYING

    def on_player_started(self, player, position):
        print('**** player started ****')
        if self.trackview.get_selected_row() is not None:

            self.control['play-pause'].get_child().set_from_gicon(
                Gio.ThemedIcon(name='media-playback-pause-symbolic'),
                Gtk.IconSize.BUTTON)
            self.control['play-pause'].set_tooltip_text(_('Pause'))

            self.trackview.get_selected_row().set_playing(True)
            if self.trackview.get_selected_row().data['position'] > 0:
                self.player.set_position(
                    self.trackview.get_selected_row().data['position'])
            if self.trackview.get_selected_row().data['duration'] == 0:
                self.update_duration()
            GLib.timeout_add_seconds(1, self.update_position)
            artists = [self.trackview.get_selected_row().data['feed_name']]
            album = self.trackview.get_selected_row().data['feed_name']
            title = self.trackview.get_selected_row().data['title']
            feed_id = self.trackview.get_selected_row().data['feed_id']
            feed_image = self.trackview.get_selected_row().data['feed_image']
            album_art = 'file://' + get_thumbnail_filename_for_feed(feed_id,
                                                                    feed_image)
            self.sound_menu.song_changed(artists, album, title, album_art)
            self.sound_menu.signal_playing()

            self.notification.update('{0} - {1}'.format(
                'uPodcatcher',
                self.trackview.get_selected_row().data['feed_name']),
                title,
                album_art)
            self.notification.show()

    def on_player_paused(self, player, position):
        print('**** player paused ****')
        if self.trackview.get_selected_row() is not None:
            self.trackview.get_selected_row().set_playing(False)

            self.control['play-pause'].get_child().set_from_gicon(
                Gio.ThemedIcon(name='media-playback-start-symbolic'),
                Gtk.IconSize.BUTTON)
            self.control['play-pause'].set_tooltip_text(_('Play'))

            position = self.player.get_position()
            self.db.set_track_position(
                self.trackview.get_selected_row().data['id'], position)
            self.trackview.get_selected_row().set_position(position)
            artists = [self.trackview.get_selected_row().data['feed_name']]
            album = self.trackview.get_selected_row().data['feed_name']
            title = self.trackview.get_selected_row().data['title']
            feed_id = self.trackview.get_selected_row().data['feed_id']
            feed_image = self.trackview.get_selected_row().data['feed_image']
            album_art = 'file://' + get_thumbnail_filename_for_feed(feed_id,
                                                                    feed_image)
            self.sound_menu.song_changed(artists, album, title, album_art)
            self.sound_menu.signal_paused()

    def on_player_stopped(self, player, position):
        pass

    def on_row_selected_changed(self, widget):
        print('-------- changed ----------',
              self.trackview.get_selected_row().data['id'])

    def on_row_activated(self, widget, row):
        print('-------- activated ----------', row.data['id'],
              self.trackview.get_selected_row().data['id'])
        if self.active_row != row:
            if self.active_row is not None:
                self.active_row.set_playing(False)
            if row != self.trackview.get_selected_row():
                self.trackview.get_selected_row().set_playing(False)
                self.trackview.select_row(row)
            self.active_row = row

        if row.data['downloaded'] == 1 and row.data['filename'] is not None\
                and os.path.exists(os.path.join(
                comun.PODCASTS_DIR, row.data['filename'])):
            if self.trackview.get_selected_row().is_playing:
                self.player.pause()
            else:
                self.player.set_filename(os.path.join(comun.PODCASTS_DIR,
                                                      row.data['filename']))
                self.player.play()
                # self.on_combo_speed_changed(self.combo_speed)
                # self.player.set_speed(value)
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
                self.get_root_window().set_cursor(
                    Gdk.Cursor(Gdk.CursorType.WATCH))
                row.set_downloading(True)

    def on_downloader_failed(self, widget, row, filename):
        if os.path.exists(filename):
            os.remove(filename)
        row.set_downloading(False)
        row.set_downloaded(False)

        self.control['play-pause'].set_sensitive(False)
        self.control['speed'].set_sensitive(False)
        self.control['position'].set_sensitive(False)

        self.db.set_track_no_downloaded(row.data['id'])

        self.get_root_window().set_cursor(
            Gdk.Cursor(Gdk.CursorType.ARROW))

    def on_downloader_ended(self, widget, row, filename):
        if os.path.exists(filename):
            filename = filename.split('/')[-1]
            self.db.set_track_downloaded(row.data['id'], filename)
            row.set_filename(filename)
            row.set_downloading(False)
            row.set_downloaded(True)

            self.control['play-pause'].set_sensitive(True)
            self.control['speed'].set_sensitive(True)
            self.control['position'].set_sensitive(True)

        self.get_root_window().set_cursor(
            Gdk.Cursor(Gdk.CursorType.ARROW))

    def on_speed_button_changed(self, widget, value):
        widget.set_label('{0}x'.format(int(value * 10) / 10))
        self.player.set_speed(value)

    def on_position_button_changed(self, widget, value):
        widget.set_label('{0}%'.format(int(value)))
        if self.trackview.get_selected_row() is not None:
            position = self.player.get_position()
            duration = self.trackview.get_selected_row().data['duration']
            if duration > 0:
                position = float(value) * float(duration) / 100
                self.trackview.get_selected_row().set_position(position)
                self.player.set_position(position)

    def init_headerbar(self):
        self.control = {}
        self.menu_selected = 'suscriptions'
        #
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = comun.APPNAME
        self.set_titlebar(hb)

        self.play_controls = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 5)
        hb.pack_start(self.play_controls)

        self.control['up'] = Gtk.Button()
        self.control['up'].set_tooltip_text(_('Goto feeds'))
        self.control['up'].add(Gtk.Image.new_from_gicon(Gio.ThemedIcon(
            name='pan-up-symbolic.symbolic'), Gtk.IconSize.BUTTON))
        self.control['up'].connect('clicked',
                                   self.on_button_up_clicked)
        self.play_controls.pack_start(self.control['up'],
                                      False, False, 0)

        self.control['speed'] = Gtk.ScaleButton()
        self.control['speed'].set_tooltip_text(_('Podcast reproduction speed'))
        self.control['speed'].set_adjustment(
            Gtk.Adjustment(1, 0.5, 4, 0.1, 0.1, 1))
        self.control['speed'].connect('value-changed',
                                      self.on_speed_button_changed)
        self.control['speed'].set_value(1)
        self.control['speed'].set_label('1.0x')
        self.play_controls.pack_start(self.control['speed'],
                                      False, False, 0)

        self.control['previous'] = Gtk.Button()
        self.control['previous'].set_tooltip_text(_('Previous'))
        self.control['previous'].add(Gtk.Image.new_from_gicon(Gio.ThemedIcon(
            name='pan-start-symbolic.symbolic'), Gtk.IconSize.BUTTON))
        self.control['previous'].connect('clicked',
                                         self._sound_menu_previous)
        self.play_controls.pack_start(self.control['previous'],
                                      False, False, 0)

        self.control['play-pause'] = Gtk.Button()
        self.control['play-pause'].set_tooltip_text(_('Play'))
        self.control['play-pause'].add(Gtk.Image.new_from_gicon(Gio.ThemedIcon(
            name='media-playback-start-symbolic'), Gtk.IconSize.BUTTON))
        self.control['play-pause'].connect('clicked',
                                           self._sound_menu_play)
        self.play_controls.pack_start(self.control['play-pause'],
                                      False, False, 0)

        self.control['next'] = Gtk.Button()
        self.control['next'].set_tooltip_text(_('Next'))
        self.control['next'].add(Gtk.Image.new_from_gicon(Gio.ThemedIcon(
            name='pan-end-symbolic.symbolic'), Gtk.IconSize.BUTTON))
        self.control['next'].connect('clicked',
                                     self._sound_menu_next)
        self.play_controls.pack_start(self.control['next'], False, False, 0)

        self.control['position'] = Gtk.ScaleButton()
        self.control['position'].set_tooltip_text(
            _('Podcast relative position'))
        self.control['position'].set_adjustment(
            Gtk.Adjustment(0, 0, 100, 1, 1, 5))
        self.control['position'].connect('value-changed',
                                         self.on_position_button_changed)
        self.control['position'].set_value(0)
        self.control['position'].set_label('0%')
        self.play_controls.pack_start(self.control['position'],
                                      False, False, 0)

        self.feed_controls = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 5)
        hb.pack_start(self.feed_controls)

        self.control['add'] = Gtk.Button()
        self.control['add'].add(Gtk.Image.new_from_gicon(Gio.ThemedIcon(
            name='list-add-symbolic'), Gtk.IconSize.BUTTON))
        self.control['add'].connect('clicked', self.on_add_feed_clicked)
        self.feed_controls.pack_start(self.control['add'],
                                      False, False, 0)
        self.control['remove'] = Gtk.Button()
        self.control['remove'].add(Gtk.Image.new_from_gicon(Gio.ThemedIcon(
            name='list-remove-symbolic'), Gtk.IconSize.BUTTON))
        self.control['remove'].connect('clicked', self.on_remove_feed_clicked)
        self.feed_controls.pack_start(self.control['remove'],
                                      False, False, 0)

        help_model = Gio.Menu()

        help_section1_model = Gio.Menu()
        help_section1_model.append(_('Homepage'), 'app.goto_homepage')
        help_section1 = Gio.MenuItem.new_section(None, help_section1_model)
        help_model.append_item(help_section1)

        help_section2_model = Gio.Menu()
        help_section2_model.append(_('Code'), 'app.goto_code')
        help_section2_model.append(_('Issues'), 'app.goto_bug')
        help_section2 = Gio.MenuItem.new_section(None, help_section2_model)
        help_model.append_item(help_section2)

        help_section3_model = Gio.Menu()
        help_section3_model.append(_('Twitter'), 'app.goto_twitter')
        help_section3_model.append(_('Facebook'), 'app.goto_facebook')
        help_section3_model.append(_('Google+'), 'app.goto_google_plus')
        help_section3 = Gio.MenuItem.new_section(None, help_section3_model)
        help_model.append_item(help_section3)

        help_section4_model = Gio.Menu()
        help_section4_model.append(_('Donations'), 'app.goto_donate')
        help_section4 = Gio.MenuItem.new_section(None, help_section4_model)
        help_model.append_item(help_section4)

        help_section5_model = Gio.Menu()
        help_section5_model.append(_('About'), 'app.about')
        help_section5 = Gio.MenuItem.new_section(None, help_section5_model)
        help_model.append_item(help_section5)

        self.control['help'] = Gtk.MenuButton()
        self.control['help'].set_menu_model(help_model)
        self.control['help'].add(Gtk.Image.new_from_gicon(Gio.ThemedIcon(
            name='open-menu-symbolic'), Gtk.IconSize.BUTTON))
        hb.pack_end(self.control['help'])

    def on_remove_feed_clicked(self, widget):
        if self.object is None and\
                self.iconview.get_selected_items()[0] is not None:
            dialog = Gtk.MessageDialog(
                self,
                0,
                Gtk.MessageType.WARNING,
                Gtk.ButtonsType.OK_CANCEL,
                _('Are you sure to delete the feed'))
            if dialog.run() == Gtk.ResponseType.OK:
                dialog.destroy()
                selected = self.iconview.get_selected_items()[0]
                model = self.iconview.get_model()
                id = model.get_value(model.get_iter(selected), 0)
                print(id)
                if self.db.remove_feed(id):
                    model.remove(model.get_iter(selected))
            else:
                dialog.destroy()

    def on_add_feed_clicked(self, widget):
        if self.object is None:
            afd = AddFeedDialog(self)
            if afd.run() == Gtk.ResponseType.ACCEPT:
                url = afd.get_url()
                if not url.startswith('http://') and\
                        not url.startswith('https://'):
                    url = 'http://' + url
                self.get_root_window().set_cursor(
                    Gdk.Cursor(Gdk.CursorType.WATCH))
                self.add_feed(url)
            afd.destroy()

    def on_toolbar_clicked(self, widget, option):
        print(widget, option)

    @async_method(on_done=lambda self,
                  result, error: self.on_add_feed_done(result, error))
    def add_feed(self, url):
        print(url)
        request = requests.get(url)
        if request.status_code == 200:
            id = self.db.add_feed(url)
            print(id)
            if id is not None:
                feed = self.db.get_feed(id)
                return feed
        return None

    def on_add_feed_done(self, result, error):
        if result is not None:
            thumbnail = os.path.join(comun.THUMBNAILS_DIR,
                                     'feed_{0}.png'.format(result['id']))
            pixbuf = get_pixbuf_from_base64string(result['image'])
            pixbuf.savev(thumbnail, 'png', [], [])
            self.storefeeds.append([result['id'],
                                    result['url'],
                                    result['title'],
                                    result['image'],
                                    result['norder'],
                                    pixbuf])
        self.get_root_window().set_cursor(
            Gdk.Cursor(Gdk.CursorType.TOP_LEFT_ARROW))

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
    Notify.init('uPodcatcher')
    app = MainApplication()
    app.run('')


if __name__ == "__main__":
    main()
