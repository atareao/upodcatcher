#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# mainwindow.py
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
import os
import requests
import mutagen
from urllib.parse import urlparse
from . import comun
from .comun import _
from .dbmanager import DBManager
from .player import Player
from .sound_menu import SoundMenuControls
from dbus.mainloop.glib import DBusGMainLoop
from .player import Status
from .async import async_method
from .addfeeddialog import AddFeedDialog
from .searchfeeddialog import SearchFeedDialog
from .itunes import PodcastClient
from .foundpodcastsdialog import FoundPodcastsDDialog
from .utils import get_pixbuf_from_base64string
from .opmlparser import create_opml_from_urls, extract_rss_urls_from_opml
from .listboxrowwithdata import ListBoxRowWithData
from .showinfodialog import ShowInfoDialog
from .downloadermanager import DownloaderManager


CSS = '''
#button:hover,
#button {
    border-image: none;
    background-image: none;
    background-color: rgba(0, 0, 0, 0);
    border-color: rgba(0, 0, 0, 0);
    border-image: none;
    border-radius: 0;
    border-width: 0;
    border-style: solid;
    text-shadow: 0 0 rgba(0, 0, 0, 0);
    -gtk-icon-effect: none;
    -gtk-icon-shadow: 0 0 rgba(0, 0, 0, 0);
    box-shadow: 0 0 rgba(0, 0, 0, 0), 0 0 rgba(0, 0, 0, 0);
}
#button:hover{
    background-color: rgba(0, 0, 0, 0.1);
}
#button:disabled{
    background-color: rgba(0, 0, 0, 0);
}
'''


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

        max_action = Gio.SimpleAction.new_stateful(
            "maximize", None, GLib.Variant.new_boolean(False))
        max_action.connect("change-state", self.on_maximize_toggle)
        self.add_action(max_action)

        import_opml = Gio.SimpleAction.new('import_opml', None)
        import_opml.connect('activate', self.on_import_opml_clicked)
        self.add_action(import_opml)

        export_opml = Gio.SimpleAction.new('export_opml', None)
        export_opml.connect('activate', self.on_export_opml_clicked)
        self.add_action(export_opml)

        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.notification = Notify.Notification.new('', '', None)

        self.object = None
        self.active_row = None
        self.updater = None

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

        # Vertical box. Contains menu and PaneView
        vbox = Gtk.VBox(False, 2)
        self.add(vbox)
        #

        # Init HeaderBar
        self.init_headerbar()

        # Init Menu
        # self.init_menu()

        # Init Toolbar
        # self.init_toolbar()
        #
        self.stack = Gtk.Stack.new()
        vbox.pack_start(self.stack, True, True, 0)

        scrolledwindow1 = Gtk.ScrolledWindow()
        scrolledwindow1.set_policy(Gtk.PolicyType.AUTOMATIC,
                                   Gtk.PolicyType.AUTOMATIC)
        scrolledwindow1.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        scrolledwindow1.set_visible(True)
        self.stack.add_named(scrolledwindow1, 'feeds')

        scrolledwindow2 = Gtk.ScrolledWindow()
        scrolledwindow2.set_policy(Gtk.PolicyType.AUTOMATIC,
                                   Gtk.PolicyType.AUTOMATIC)
        scrolledwindow2.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        scrolledwindow2.set_visible(True)
        self.stack.add_named(scrolledwindow2, 'tracks')
        self.stack.set_transition_type(Gtk.StackTransitionType.UNDER_DOWN)

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
        scrolledwindow1.add(self.iconview)

        self.trackview = Gtk.ListBox()
        self.trackview.connect('row-activated', self.on_row_activated)
        self.trackview.connect('row-selected', self.on_row_selected)
        self.trackview.connect('selected-rows-changed',
                               self.on_row_selected_changed)
        # self.trackview.set_activate_on_single_click(False)
        self.trackview.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        scrolledwindow2.add(self.trackview)

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

        self.downloaderManager = DownloaderManager()

        self.load_css()
        self.show_all()
        self.stack.set_visible_child_name('feeds')
        self.stack.get_visible_child().show_all()
        self.play_controls.set_visible(False)
        self.feed_controls.set_visible(True)

    def on_import_opml_clicked(self, widget, action):
        dialog = Gtk.FileChooserDialog(_(
            'Select one opml file'),
            self,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_current_folder(os.path.expanduser('~'))
        dialog.set_select_multiple(False)
        filter = Gtk.FileFilter()
        filter.set_name(_('Opml file'))
        filter.add_pattern('*.opml')
        dialog.add_filter(filter)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            dialog.destroy()
            with open(filename, 'r') as f:
                opmlstring = f.read()
                urls = extract_rss_urls_from_opml(opmlstring)
                for url in urls:
                    self.get_root_window().set_cursor(
                        Gdk.Cursor(Gdk.CursorType.WATCH))
                    self.add_feed(url)
        else:
            dialog.destroy()

    def on_export_opml_clicked(self, widget, action):
        dialog = Gtk.FileChooserDialog(_(
            'Select one opml file'),
            self,
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_current_folder(os.path.expanduser('~'))
        dialog.set_select_multiple(False)
        filter = Gtk.FileFilter()
        filter.set_name(_('Opml file'))
        filter.add_pattern('*.opml')
        dialog.add_filter(filter)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            dialog.destroy()
            if not filename.endswith('.opml'):
                filename += '.opml'
            feeds = self.db.get_feeds()
            urls = []
            for feed in feeds:
                urls.append(feed['url'])
            opmlstring = create_opml_from_urls(urls)
            with open(filename, 'w') as f:
                f.write(opmlstring)
        else:
            dialog.destroy()

    def on_equalizer_value_changed(self, widget, value):
        widget.set_label('{0}\n17Hz'.format(int(value)))

    def on_maximize_toggle(self, action, value):
            action.set_state(value)
            if value.get_boolean():
                self.maximize()
            else:
                self.unmaximize()

    def on_row_download_started(self, widget, row):
        row.set_downloading(True)

    def on_row_download_ended(self, widget, row):
        row.set_downloading(False)
        path = urlparse(row.data['url']).path
        extension = os.path.splitext(path)[1]
        filename = 'podcast_{0}{1}'.format(row.data['id'], extension)
        pathandfile = os.path.join(comun.PODCASTS_DIR, filename)
        if os.path.exists(pathandfile):
            filetype = mutagen.File(pathandfile)
            duration = filetype.info.length
            self.db.set_track_downloaded(row.data['id'], filename)
            self.db.set_track_duration(row.data['id'], duration)
            row.set_downloaded(True)
            row.data['filename'] = filename
            row.set_duration(duration)
        else:
            row.set_downloaded(False)
            self.db.set_track_no_downloaded(row.data['id'])
            row.data['filename'] = ''

    def on_row_download_failed(self, widget, row):
        row.set_downloading(False)
        row.set_downloaded(False)
        self.db.set_track_no_downloaded(row.data['id'])
        row.data['filename'] = ''

    def on_row_download(self, widget, row):
        if row.is_downloaded is True:
            path = urlparse(row.data['url']).path
            extension = os.path.splitext(path)[1]
            filename = os.path.join(
                comun.PODCASTS_DIR,
                'podcast_{0}{1}'.format(row.data['id'], extension))
            if os.path.exists(filename):
                os.remove(filename)
                self.db.set_track_no_downloaded(row.data['id'])
                row.data['filename'] = ''
                row.set_downloaded(False)
        else:
            self.downloaderManager.add(row)
            self.downloaderManager.connect('started',
                                           self.on_row_download_started)
            self.downloaderManager.connect('ended',
                                           self.on_row_download_ended)
            self.downloaderManager.connect('failed',
                                           self.on_row_download_failed)

    def on_row_listened(self, widget, row):
        listened = not (row.data['listened'] == 1)
        row.set_listened(listened)
        if listened:
            self.db.set_track_listened(row.data['id'])
        else:
            self.db.set_track_no_listened(row.data['id'])

    def on_row_info(self, widget, row):
        sid = ShowInfoDialog(self,
                             row.data['feed_name'],
                             row.data['title'],
                             row.data['link'],
                             row.data['description'])
        sid.run()
        sid.hide()
        sid.destroy()

    def on_row_play(self, widget, row):
        print('old',
              self.active_row.index if self.active_row is not None else None,
              'new',
              row.index)
        if self.active_row is not None and self.active_row != row and\
                self.active_row.is_playing is True:
            self.active_row.set_playing(False)
            self.player.pause()
            self.control['play-pause'].get_child().set_from_gicon(
                Gio.ThemedIcon(name='media-playback-start-symbolic'),
                Gtk.IconSize.BUTTON)
            self.control['play-pause'].set_tooltip_text(_('Play'))
            self.db.set_track_position(self.active_row.data['id'],
                                       self.active_row.data['position'])
        self.active_row = row
        if self.active_row.is_playing is False:
            self.player.set_filename(
                os.path.join(comun.PODCASTS_DIR,
                             self.active_row.data['filename']))
            fraction = (float(self.active_row.data['position']) /
                        float(self.active_row.data['duration']))
            self.control['position'].handler_block_by_func(
                self.on_position_button_changed)
            self.control['position'].set_value(fraction)
            self.control['label-position'].set_text(
                _('Position') + ': {0}%'.format(int(fraction * 100)))
            self.control['position'].handler_unblock_by_func(
                self.on_position_button_changed)
            self.control['play-pause'].get_child().set_from_gicon(
                Gio.ThemedIcon(name='media-playback-pause-symbolic'),
                Gtk.IconSize.BUTTON)
            self.control['play-pause'].set_tooltip_text(_('Pause'))
            if self.active_row.data['position'] > 0:
                self.player.set_position(
                    self.active_row.data['position'])
            if self.active_row.data['duration'] == 0:
                self.update_duration()
            artists = [self.active_row.data['feed_name']]
            album = self.active_row.data['feed_name']
            title = self.active_row.data['title']
            feed_id = self.active_row.data['feed_id']
            feed_image = self.active_row.data['feed_image']
            album_art = 'file://' + get_thumbnail_filename_for_feed(feed_id,
                                                                    feed_image)
            self.sound_menu.song_changed(artists, album, title, album_art)
            self.sound_menu.signal_playing()

            self.notification.update('{0} - {1}'.format(
                'uPodcatcher',
                album),
                title,
                album_art)
            self.notification.show()
            #
            if self.active_row.data['position'] > 0:
                self.player.set_position(
                    self.active_row.data['position'])
            self.player.play()
            self.updater = GLib.timeout_add_seconds(1, self.update_position)
            self.active_row.set_playing(True)
        else:
            artists = [self.active_row.data['feed_name']]
            album = self.active_row.data['feed_name']
            title = self.active_row.data['title']
            feed_id = self.active_row.data['feed_id']
            feed_image = self.active_row.data['feed_image']
            album_art = 'file://' + get_thumbnail_filename_for_feed(feed_id,
                                                                    feed_image)
            self.sound_menu.song_changed(artists, album, title, album_art)
            self.sound_menu.signal_paused()

            self.player.pause()
            self.control['play-pause'].get_child().set_from_gicon(
                Gio.ThemedIcon(name='media-playback-start-symbolic'),
                Gtk.IconSize.BUTTON)
            self.control['play-pause'].set_tooltip_text(_('Play'))

            self.active_row.set_playing(False)
            self.db.set_track_position(self.active_row.data['id'],
                                       self.active_row.data['position'])

    def on_iconview_actived(self, widget, index):
        model = widget.get_model()
        selected = widget.get_selected_items()[0]
        id = model.get_value(model.get_iter(selected), 0)
        self.object = self.db.get_feed(id)
        for awidget in self.trackview.get_children():
            self.trackview.remove(awidget)
        # self.db.add_tracks(id)
        for index, track in enumerate(self.db.get_tracks_from_feed(id)):
            row = ListBoxRowWithData(track, index)
            row.connect('button_play_pause_clicked', self.on_row_play, row)
            row.connect('button_info_clicked', self.on_row_info, row)
            row.connect('button_listened_clicked', self.on_row_listened, row)
            row.connect('button_download_clicked', self.on_row_download, row)
            row.show()
            self.trackview.add(row)
        widget.hide()

        self.get_root_window().set_cursor(
            Gdk.Cursor(Gdk.CursorType.WATCH))

        self.update_tracks(id)
        self.stack.set_visible_child_name('tracks')
        self.stack.get_visible_child().show_all()
        self.play_controls.set_visible(True)
        self.feed_controls.set_visible(False)
        row = self.trackview.get_row_at_index(0)
        self.trackview.handler_block_by_func(self.on_row_selected)
        self.trackview.select_row(row)
        self.trackview.handler_unblock_by_func(self.on_row_selected)

    @async_method(on_done=lambda self, result, error:
                  self.on_update_tracks_done(result, error))
    def update_tracks(self, id):
        print('updating....', id)
        result = None
        last_track = self.db.get_last_track_from_feed(id)
        last_feed_track = self.db.get_last_track_date(id)
        if last_track['date'] is None or last_feed_track > last_track['date']:
            self.db.add_tracks(id, last_track['date'])
            result = (id, last_track['date'])
        return result

    def on_update_tracks_done(self, result, error):
        if error is None and result is not None:
            tracks = self.db.get_tracks_from_feed(*result)
            tracks.reverse()
            for index, track in enumerate(tracks):
                row = ListBoxRowWithData(track, index)
                row.connect('button_play_pause_clicked', self.on_row_play, row)
                row.connect('button_info_clicked', self.on_row_info, row)
                row.connect('button_listened_clicked', self.on_row_listened,
                            row)
                row.connect('button_download_clicked', self.on_row_download,
                            row)
                row.show()
                self.trackview.prepend(row)
            self.trackview.show_all()
            '''
            self.scrolledwindow2.set_visible(True)
            self.scrolledwindow2.show_all()
            '''
        self.get_root_window().set_cursor(
            Gdk.Cursor(Gdk.CursorType.TOP_LEFT_ARROW))

    def kill_updater(self):
        if self.updater is not None:
            GLib.source_remove(self.updater)
            self.updater = None

    def on_button_up_clicked(self, widget):
        if self.active_row is not None and self.active_row.is_playing:
            self.active_row.click_button_play()
        self.stack.set_visible_child_name('feeds')
        self.stack.get_visible_child().show_all()
        self.play_controls.set_visible(False)
        self.feed_controls.set_visible(True)
        self.object = None

    def _sound_menu_is_playing(self):
        return self.player.status == Status.PLAYING

    def _sound_menu_play(self, *args):
        """Play"""
        # self.is_playing = True  # Need to overwrite
        row = self.active_row
        if row is None:
            row = self.trackview.get_row_at_index(0)
            self.active_row = row
        self.active_row.click_button_play()

    def _sound_menu_stop(self):
        """Pause"""
        if self.active_row is not None and self.active_row.is_playing is True:
            self.active_row.click_button_play()

    def _sound_menu_pause(self, *args):
        """Pause"""
        if self.active_row is not None:
            self.active_row.click_button_play()

    def _sound_menu_next(self, *args):
        """Next"""
        index = self.get_next_playable_track()
        if index is not None:
            row = self.trackview.get_row_at_index(index)
            row.click_button_play()

    def _sound_menu_previous(self, *args):
        """Previous"""
        index = self.get_previous_playable_track()
        if index is not None:
            row = self.trackview.get_row_at_index(index)
            row.click_button_play()

    def _sound_menu_raise(self):
        """Click on player"""
        self.show()

    def on_row_selected(self, widget, row):
        pass

    def get_playable_tracks(self):
        playables = []
        for index in range(0, len(self.trackview.get_children())):
            if self.trackview.get_row_at_index(index).can_play():
                playables.append(index)
        return sorted(playables)

    def get_next_playable_track(self):
        playables = self.get_playable_tracks()
        if len(playables) > 0:
            if self.active_row is not None and\
                    self.active_row.index in playables:
                selected = playables.index(self.active_row.index)
                next = selected + 1
                if next >= len(playables):
                    next = 0
                return playables[next]
            else:
                return playables[0]
        return None

    def get_previous_playable_track(self):
        playables = self.get_playable_tracks()
        if len(playables) > 0:
            if self.active_row is not None and\
                    self.active_row.index in playables:
                selected = playables.index(self.active_row.index)
                previous = selected - 1
                if previous < 0:
                    previous = len(playables) - 1
                return playables[previous]
            else:
                return playables[0]
        return None

    def update_duration(self):
        if self.active_row is not None:
            duration = self.player.get_duration()
            self.db.set_track_duration(
                self.active_row.data['id'], duration)
            self.active_row.set_duration(duration)
        return False

    def update_position(self):
        if self.active_row is not None:
            position = self.player.get_position()
            duration = self.active_row.data['duration']
            if duration > 0:
                fraction = float(position) / float(duration)
                if fraction >= 1.0:
                    self.db.set_track_listened(
                        self.active_row.data['id'])
                    self.active_row.set_listened(True)
                self.active_row.set_position(position)

                self.control['position'].handler_block_by_func(
                    self.on_position_button_changed)
                self.control['position'].set_value(int(fraction * 100))
                self.control['label-position'].set_text(
                    _('Position') + ': {0}%'.format(int(fraction * 100)))
                self.control['position'].handler_unblock_by_func(
                    self.on_position_button_changed)

            return self.player.status == Status.PLAYING

    def on_player_started(self, player, position):
        pass

    def on_player_paused(self, player, position):
        pass

    def on_player_stopped(self, player, position):
        pass

    def on_row_selected_changed(self, widget):
        pass

    def on_row_activated(self, widget, row):
        pass

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
            filetype = mutagen.File(filename)
            duration = filetype.info.length
            filename = filename.split('/')[-1]

            self.db.set_track_downloaded(row.data['id'], filename)
            self.db.set_track_duration(row.data['id'], duration)

            row.set_duration(duration)
            row.set_filename(filename)
            row.set_downloading(False)
            row.set_downloaded(True)

            self.control['play-pause'].set_sensitive(True)
            self.control['speed'].set_sensitive(True)
            self.control['position'].set_sensitive(True)

        self.get_root_window().set_cursor(
            Gdk.Cursor(Gdk.CursorType.ARROW))

    def on_remove_silence_changed(self, widget, value):
        print(widget.get_active(), value)
        self.player.set_remove_silence(widget.get_active())

    def on_speed_button_changed(self, widget):
        value = widget.get_value()
        self.control['label-speed'].set_text(
            _('Speed') + ': {0}x'.format(int(value * 10) / 10))
        self.player.set_speed(value)

    def on_position_button_changed(self, widget):
        value = widget.get_value()
        self.control['label-position'].set_label(
            _('Position' + ': {0}%'.format(int(value))))
        if self.active_row is not None:
            position = self.player.get_position()
            duration = self.active_row.data['duration']
            if duration > 0:
                position = float(value) * float(duration) / 100
                self.active_row.set_position(position)
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
            name='go-up-symbolic'), Gtk.IconSize.BUTTON))
        self.control['up'].connect('clicked',
                                   self.on_button_up_clicked)
        self.play_controls.pack_start(self.control['up'],
                                      False, False, 0)

        popover = Gtk.Popover()
        popover_grid = Gtk.Grid()
        popover.add(popover_grid)
        self.control['label-position'] = Gtk.Label(_('Position') + ':')
        self.control['label-position'].set_alignment(0, 0.5)
        popover_grid.attach(self.control['label-position'], 0, 0, 5, 1)
        self.control['position'] = Gtk.Scale()
        self.control['position'].set_tooltip_text(
            _('Podcast relative position'))
        self.control['position'].set_adjustment(
            Gtk.Adjustment(0, 0, 100, 1, 1, 5))
        self.control['position'].connect('value-changed',
                                         self.on_position_button_changed)
        self.control['position'].set_value(0)
        popover_grid.attach(self.control['position'], 5, 0, 5, 1)

        self.control['label-speed'] = Gtk.Label(_('Speed') + ':')
        self.control['label-speed'].set_alignment(0, 0.5)
        popover_grid.attach(self.control['label-speed'], 0, 1, 5, 1)
        self.control['speed'] = Gtk.Scale()
        self.control['speed'].set_adjustment(Gtk.Adjustment(
            1, 0.5, 4, 0.1, 0.1, 1))
        self.control['speed'].set_size_request(200, 0)
        self.control['speed'].connect('value-changed',
                                      self.on_speed_button_changed)
        self.control['speed'].set_value(1)
        popover_grid.attach(self.control['speed'], 5, 1, 5, 1)

        label = Gtk.Label(_('Remove silence') + ':')
        label.set_alignment(0, 0.5)
        popover_grid.attach(label, 0, 2, 5, 1)

        self.control['remove-silence'] = Gtk.Switch()
        self.control['remove-silence'].connect(
            'notify::active', self.on_remove_silence_changed)
        tbox = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)
        tbox.add(self.control['remove-silence'])
        popover_grid.attach(tbox, 5, 2, 5, 1)

        popover_grid.attach(Gtk.Label(_('Equalizer')), 0, 3, 10, 1)

        for index in range(0, 10):
            band = 'band{0}'.format(index)
            self.control[band] = Gtk.Scale.new_with_range(
                Gtk.Orientation.VERTICAL, -24.0, 12.0, 0.1)
            self.control[band].set_size_request(0, 200)
            self.control[band].set_value(0)
            popover_grid.attach(self.control[band], index, 4, 1, 1)

        popover_grid.show_all()

        self.control['configuration'] = Gtk.MenuButton()
        self.control['configuration'].set_tooltip_text(_('Configuration'))
        self.control['configuration'].add(
            Gtk.Image.new_from_gicon(Gio.ThemedIcon(
                name='preferences-system-symbolic'), Gtk.IconSize.BUTTON))
        self.control['configuration'].set_popover(popover)
        self.play_controls.pack_start(self.control['configuration'],
                                      False, False, 0)

        self.control['previous'] = Gtk.Button()
        self.control['previous'].set_tooltip_text(_('Previous'))
        self.control['previous'].add(Gtk.Image.new_from_gicon(Gio.ThemedIcon(
            name='go-next-symbolic-rtl'), Gtk.IconSize.BUTTON))
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
            name='go-next-symbolic'), Gtk.IconSize.BUTTON))
        self.control['next'].connect('clicked',
                                     self._sound_menu_next)
        self.play_controls.pack_start(self.control['next'], False, False, 0)

        '''
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
        '''

        self.feed_controls = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 5)
        hb.pack_start(self.feed_controls)

        self.control['search'] = Gtk.Button()
        self.control['search'].add(Gtk.Image.new_from_gicon(Gio.ThemedIcon(
            name='system-search-symbolic'), Gtk.IconSize.BUTTON))
        self.control['search'].connect('clicked', self.on_search_feed_clicked)
        self.feed_controls.pack_start(self.control['search'],
                                      False, False, 0)
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

        help_section0_model = Gio.Menu()
        help_section0_model.append(_('Import opml'), 'win.import_opml')
        help_section0_model.append(_('Export opml'), 'win.export_opml')
        help_section0 = Gio.MenuItem.new_section(None, help_section0_model)
        help_model.append_item(help_section0)

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

    def on_search_feed_clicked(self, widget):
        if self.object is None:
            sfd = SearchFeedDialog(self)
            if sfd.run() == Gtk.ResponseType.ACCEPT:
                query = sfd.get_query()
                self.get_root_window().set_cursor(
                    Gdk.Cursor(Gdk.CursorType.WATCH))
                self.search_feed(query)
            sfd.destroy()

    @async_method(on_done=lambda self,
                  result, error: self.on_search_feed_done(result, error))
    def search_feed(self, query):
        try:
            itp = PodcastClient()
            return itp.search(query)
        except Exception as e:
            print(e)
        return None

    def on_search_feed_done(self, result, error):
        if result is not None and len(result) > 0:
            fpd = FoundPodcastsDDialog(self, result)
            if fpd.run() == Gtk.ResponseType.ACCEPT:
                selecteds = fpd.get_selecteds()
                fpd.destroy()
                for selected in selecteds:
                    self.get_root_window().set_cursor(
                        Gdk.Cursor(Gdk.CursorType.WATCH))
                    self.add_feed(selected['url'])
            else:
                fpd.destroy()
                self.get_root_window().set_cursor(
                    Gdk.Cursor(Gdk.CursorType.TOP_LEFT_ARROW))
        else:
            self.get_root_window().set_cursor(
                Gdk.Cursor(Gdk.CursorType.WATCH))

    def on_remove_feed_clicked(self, widget):
        if self.object is None and\
                self.iconview.get_selected_items()[0] is not None:
            if len(self.iconview.get_selected_items()) > 1:
                msg = _('Are you sure to delete the feeds')
            else:
                msg = _('Are you sure to delete the feed')
            dialog = Gtk.MessageDialog(
                self,
                0,
                Gtk.MessageType.WARNING,
                Gtk.ButtonsType.OK_CANCEL,
                msg)
            if dialog.run() == Gtk.ResponseType.OK:
                dialog.destroy()
                model = self.iconview.get_model()
                for selected in self.iconview.get_selected_items():
                    id = model.get_value(model.get_iter(selected), 0)
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
        pass

    @async_method(on_done=lambda self,
                  result, error: self.on_add_feed_done(result, error))
    def add_feed(self, url):
        request = requests.get(url)
        if request.status_code == 200:
            id = self.db.add_feed(url)
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

    def load_css(self):
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER)
