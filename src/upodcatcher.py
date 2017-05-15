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
import base64
import comun
from comun import _
from dbmanager import DBManager
from player import Player
from downloader import Downloader
from sound_menu import SoundMenuControls
from dbus.mainloop.glib import DBusGMainLoop
from player import Status


PLAY = GdkPixbuf.Pixbuf.new_from_file_at_size(comun.PLAY_ICON, 32, 32)
PAUSE = GdkPixbuf.Pixbuf.new_from_file_at_size(comun.PAUSE_ICON, 32, 32)
DOWNLOAD = GdkPixbuf.Pixbuf.new_from_file_at_size(comun.DOWNLOAD_ICON, 32, 32)


def get_pixbuf_from_base64string(base64string):
    raw_data = base64.b64decode(base64string.encode())
    pixbuf_loader = GdkPixbuf.PixbufLoader.new_with_mime_type("image/png")
    pixbuf_loader.write(raw_data)
    pixbuf_loader.close()
    pixbuf = pixbuf_loader.get_pixbuf()
    return pixbuf


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
        self.downloading = downloading
        if downloading is True:
            self.play_pause.set_from_pixbuf(DOWNLOAD)
        else:
            self.play_pause.set_from_pixbuf(PLAY)

    def set_playing(self, playing):
        print(playing)
        self.is_playing = playing
        if playing is True:
            self.play_pause.set_from_pixbuf(PAUSE)
        else:
            self.play_pause.set_from_pixbuf(PLAY)

    def __eq__(self, other):
        return self.data[0] == other.data[0]

    def set_data(self, data):
        self.data = data
        self.image.set_from_pixbuf(get_pixbuf_from_base64string(data[2]))
        self.label1.set_markup(
            '<big><b>{0}</b></big>'.format(data[1]))
        self.label2.set_text(data[5])
        self.label3.set_text('00:00:00')
        self.label4.set_text('00:00:00')
        if data[9] is None:
            self.play_pause.set_from_pixbuf(DOWNLOAD)
        else:
            if os.path.exists(os.path.join(comun.DATADIR, data[9])):
                self.play_pause.set_from_pixbuf(PLAY)
            else:
                self.play_pause.set_from_pixbuf(DOWNLOAD)


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
        print('---', widget, action, parameter)
        self.win.menu['lists'].set_label(action.get_string())
        widget.set_state(action)

    def heading(self, action):
        print(action)

    def toggle_heading(self, action, state):
        print(action, state)

    def do_activate(self):
        print('activate')
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
        self.set_default_size(300, 600)
        self.builder = Gtk.Builder()
        self.builder.add_from_file(comun.UI_FILE)
        # self.connect('delete-event', self.on_close_application)
        # self.connect('realize', self.on_activate_preview_or_html)
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        # Vertical box. Contains menu and PaneView
        vbox = Gtk.VBox(False, 2)
        self.previous_row = None
        self.current_row = None

        self.player = Player()

        DBusGMainLoop(set_as_default=True)
        self.sound_menu = SoundMenuControls('uPodcatcher')
        self.sound_menu._sound_menu_is_playing = self._sound_menu_is_playing
        self.sound_menu._sound_menu_play = self._sound_menu_play
        self.sound_menu._sound_menu_pause = self._sound_menu_pause
        self.sound_menu._sound_menu_next = self._sound_menu_next
        self.sound_menu._sound_menu_previous = self._sound_menu_previous
        self.sound_menu._sound_menu_raise = self._sound_menu_raise

        self.add(vbox)
        #

        # Init HeaderBar
        self.init_headerbar()

        # Init Menu
        # self.init_menu()

        # Init Toolbar
        # self.init_toolbar()
        #
        scrolledwindow = Gtk.ScrolledWindow()
        scrolledwindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                  Gtk.PolicyType.AUTOMATIC)
        scrolledwindow.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        vbox.pack_start(scrolledwindow, True, True, 0)

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
        #scrolledwindow.add(self.iconview)

        self.trackview = Gtk.ListBox()
        self.trackview.connect('row-activated', self.on_row_activated)
        self.trackview.connect('row-selected', self.on_row_selected)
        self.trackview.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scrolledwindow.add(self.trackview)

        # StatusBar
        self.statusbar = Gtk.Statusbar()
        vbox.pack_start(self.statusbar, False, False, 0)
        #
        self.db = DBManager(False)
        for feed in self.db.get_feeds():
            pixbuf = get_pixbuf_from_base64string(feed[3])
            self.storefeeds.append([feed[0],
                                    feed[1],
                                    feed[2],
                                    feed[3],
                                    feed[4],
                                    pixbuf])

        for track in self.db.get_tracks():
            self.trackview.add(ListBoxRowWithData(track))

        self.show_all()

    def _sound_menu_is_playing(self):
        return self.player.status == Status.PLAYING

    def _sound_menu_play(self):
        """Play"""
        # self.is_playing = True  # Need to overwrite
        self.player.play()

    def _sound_menu_pause(self):
        """Pause"""
        # self.is_playing = False  # Need to overwrite
        self.player.pause()

    def _sound_menu_next(self):
        """Next"""
        index = self.current_row.get_index()
        index += 1
        if index > len(self.trackview.get_children()) - 1:
            index = 0
        current_row = self.trackview.get_row_at_index(index)
        self.trackview.select_row(current_row)

    def _sound_menu_previous(self):
        """Previous"""
        index = self.current_row.get_index()
        index -= 1
        if index < 0:
            index = len(self.trackview.get_children()) - 1
        current_row = self.trackview.get_row_at_index(index)
        self.trackview.select_row(current_row)

    def _sound_menu_raise(self):
        """Click on player"""
        self.win_preferences.show()

    def on_row_selected(self, widget, row):
        self.previous_row = self.current_row
        self.current_row = row

    def on_row_activated(self, widget, row):
        print('row_activated', row.get_index())
        exists = False
        if row.data[9] is not None:
            filename = os.path.join(comun.PODCASTS_DIR, row.data[9])
            if os.path.exists(filename):
                exists = True
                if self.current_row is not None:
                    if self.current_row == row:
                        if self.current_row.is_playing:
                            self.player.pause()
                            self.current_row.set_playing(False)
                        else:
                            self.player.play()
                            self.sound_menu.song_changed('', '', 'Title of the song', None) #Icon)
                            self.current_row.set_playing(True)
                    else:
                        if self.current_row.is_playing:
                            self.player.pause()
                            self.current_row.set_playing(False)
                            self.player.set_sound(filename)
                            self.player.play()
                            row.set_playing(True)
                            self.current_row = row
                else:
                    self.current_row = row
                    self.player.set_sound(filename)
                    self.player.play()
                    self.current_row.set_playing(True)
        if exists is False:
            url = row.data[6]
            ext = url.split('.')[-1]
            filename = os.path.join(comun.PODCASTS_DIR,
                                    'podcast_{0}.{1}'.format(row.data[0], ext))
            if row.is_downloading is False:
                downloader = Downloader(url, filename)
                downloader.connect('ended', self.on_downloader_ended,
                                   row, filename)
                downloader.connect('failed', self.on_downloader_failed,
                                   row, filename)
                print('started')
                downloader.start()
                row.set_downloading(True)

    def on_downloader_failed(self, widget, row, filename):
        print('failed')
        if os.path.exists(filename):
            os.remove(filename)
        row.set_downloading(True)
        row.is_downloading = False

    def on_downloader_ended(self, widget, row, filename):
        self.db.set_track_downloaded(row.data[0], filename.split('/')[-1])
        ans = self.db.get_track(row.data[0])
        if ans is not None:
            row.set_data(ans)

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

        self.menu['open'] = Gtk.MenuButton(_('Open'))
        self.menu['open'].set_menu_model(self.builder.get_object('open-menu'))
        hb.pack_start(self.menu['open'])

        self.menu['new-tab'] = Gtk.Button()
        self.menu['new-tab'].set_image(
            Gtk.Image.new_from_pixbuf(icontheme.load_icon_for_scale(
                'tab-new-symbolic', 16, 1,
                Gtk.IconLookupFlags.FORCE_SIZE)))
        self.menu['new-tab'].set_tooltip_text(_('New tab'))
        self.menu['new-tab'].connect(
            'clicked', self.on_toolbar_clicked, 'new-tab')
        hb.pack_start(self.menu['new-tab'])

        self.menu['tools'] = Gtk.MenuButton()
        self.menu['tools'].set_image(
            Gtk.Image.new_from_pixbuf(icontheme.load_icon_for_scale(
                'format-justify-fill-symbolic', 16, 1,
                Gtk.IconLookupFlags.FORCE_SIZE)))
        self.menu['tools'].set_tooltip_text(_('Tools'))
        self.menu['tools'].set_popover(self.builder.get_object("tools"))
        hb.pack_end(self.menu['tools'])

        self.menu['preview'] = Gtk.Button()
        self.menu['preview'].set_image(
            Gtk.Image.new_from_pixbuf(icontheme.load_icon_for_scale(
                'weather-clear-symbolic', 16, 1,
                Gtk.IconLookupFlags.FORCE_SIZE)))
        self.menu['preview'].set_tooltip_text(_('Preview'))
        self.menu['preview'].connect(
            'clicked', self.on_toolbar_clicked, 'preview')
        hb.pack_end(self.menu['preview'])

        self.menu['search'] = Gtk.Button()
        self.menu['search'].set_image(
            Gtk.Image.new_from_pixbuf(icontheme.load_icon_for_scale(
                'preferences-system-search-symbolic', 16, 1,
                Gtk.IconLookupFlags.FORCE_SIZE)))
        self.menu['search'].set_tooltip_text(_('Search'))
        self.menu['search'].connect(
            'clicked', self.on_toolbar_clicked, 'search')
        hb.pack_end(self.menu['search'])

        self.menu['save'] = Gtk.Button(_('Save'))
        hb.pack_end(self.menu['save'])

    def on_toolbar_clicked(self, widget, option):
        print(widget, option)

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
