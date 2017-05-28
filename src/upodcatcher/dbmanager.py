#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# dbmanager.py
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

import sqlite3
from . import comun
import requests
import feedparser
import io
import os
import base64
from PIL import Image
from dateutil.parser import parse
from .upod_classes import Feed, Track

SQLStartString = '''
DROP TABLE if exists FEEDS;
DROP TABLE if exists LISTS;
DROP TABLE if exists TRACKS;
DROP TABLE if exists LIST;
DROP VIEW if exists TRACKS_FEED_VIEW;
DROP VIEW if exists TRACKS_LIST_VIEW;
'''

SQLString = '''
CREATE TABLE if not exists FEEDS (
    ID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
    URL TEXT UNIQUE NOT NULL,
    TITLE TEXT UNIQUE NOT NULL,
    IMAGE TEXT,
    NORDER INTEGER);
CREATE TABLE if not exists LISTS (
    ID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
    NAME TEXT UNIQUE NOT NULL,
    NORDER INTEGER);
CREATE TABLE if not exists TRACKS (
    ID INTEGER UNIQUE NOT NULL PRIMARY KEY AUTOINCREMENT,
    FEED_ID INTEGER REFERENCES FEEDS (ID) ON DELETE CASCADE NOT NULL,
    IDEN TEXT UNIQUE NOT NULL,
    DATE TEXT NOT NULL,
    TITLE TEXT NOT NULL,
    URL TEXT UNIQUE NOT NULL,
    DURATION INTEGER NOT NULL DEFAULT 0,
    POSITION INTEGER NOT NULL DEFAULT 0,
    DOWNLOADED INTEGER NOT NULL DEFAULT 0,
    LISTENED INTEGER NOT NULL DEFAULT 0,
    FILENAME TEXT,
    NORDER INTEGER);
CREATE TABLE if not exists LIST (
    ID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
    LIST_ID INTEGER REFERENCES LISTS (ID) ON DELETE CASCADE,
    TRACK_ID INTEGER REFERENCES TRACKS (ID) ON DELETE CASCADE,
    POSITION INTEGER NOT NULL DEFAULT 0,
    LISTENED INTEGER NOT NULL DEFAULT 0,
    NORDER INTEGER,
    UNIQUE (LIST_ID, TRACK_ID) ON CONFLICT IGNORE);

CREATE VIEW if not exists TRACKS_FEED_VIEW AS
    SELECT
        TRACKS.ID,
        FEEDS.ID as FEED_ID,
        TRACKS.IDEN,
        TRACKS.DATE,
        TRACKS.TITLE,
        TRACKS.URL,
        TRACKS.DURATION,
        TRACKS.POSITION,
        TRACKS.DOWNLOADED,
        TRACKS.LISTENED,
        TRACKS.FILENAME,
        TRACKS.NORDER,
        FEEDS.TITLE AS PODCAST_NAME,
        FEEDS.IMAGE AS PODCAST_IMAGE
      FROM TRACKS
      LEFT JOIN FEEDS ON TRACKS.FEED_ID = FEEDS.ID
      ORDER BY TRACKS.NORDER;

CREATE VIEW if not exists TRACKS_LIST_VIEW AS
    SELECT
        TRACKS.ID,
        TRACKS.FEED_ID,
        TRACKS.IDEN,
        TRACKS.DATE,
        TRACKS.TITLE,
        TRACKS.URL,
        TRACKS.DURATION,
        LIST.POSITION,
        TRACKS.DOWNLOADED,
        LIST.LISTENED,
        TRACKS.FILENAME,
        LIST.NORDER,
        FEEDS.TITLE AS PODCAST_NAME,
        FEEDS.IMAGE AS PODCAST_IMAGE,
        LIST.LIST_ID AS LIST_ID
    FROM LIST
    LEFT JOIN LISTS ON LIST.LIST_ID = LISTS.ID
    LEFT JOIN TRACKS ON LIST.TRACK_ID = TRACKS.ID
    LEFT JOIN FEEDS ON TRACKS.FEED_ID = FEEDS.ID
    ORDER BY LIST.NORDER;


INSERT OR IGNORE INTO LISTS (NAME, NORDER) VALUES ('All', 1);
'''


def create_base64(image_url):
    base64string = None
    print(image_url)
    try:
        r = requests.get(image_url, timeout=5, verify=False)
        if r.status_code == 200:
            writer_file = io.BytesIO()
            for chunk in r.iter_content(1024):
                writer_file.write(chunk)
            old_image = Image.open(writer_file)
            old_image.thumbnail((128, 128), Image.ANTIALIAS)
            new_image = io.BytesIO()
            old_image.save(new_image, "png")
            base64string = base64.b64encode(new_image.getvalue())
    except Exception as e:
        print(e)
    if base64string is not None:
        return base64string.decode()
    return None


class DBManager():
    def __init__(self, restart=False):
        if not os.path.exists(comun.CONFIG_APP_DIR):
            os.makedirs(comun.CONFIG_APP_DIR)
        if not os.path.exists(comun.DATABASE):
            restart = True
        self.db = sqlite3.connect(comun.DATABASE, check_same_thread=False)
        cursor = self.db.cursor()
        if restart is True:
            cursor.executescript(SQLStartString)
        cursor.executescript(SQLString)
        self.db.commit()

    def restart(self):
        cursor = self.db.cursor()
        cursor.executescript(SQLStartString)
        cursor.executescript(SQLString)
        self.db.commit()

    def remove_feed(self, id):
        cursor = self.db.cursor()
        ans = False
        try:
            cursor.execute(
                '''PRAGMA foreign_keys=ON;''')
            cursor.execute(
                '''DELETE FROM FEEDS WHERE ID=?''', (id,))
            self.db.commit()
            ans = True
        except Exception as e:
            print('---', e, '---')
        cursor.close()
        return ans

    def add_feed(self, url):
        ans = None
        r = requests.get(url, verify=False)
        if r.status_code == 200:
            d = feedparser.parse(r.text)
            title = d.feed.title
            image_url = d.feed.image.url
            image = create_base64(image_url)
            norder = self.get_max_norder('FEEDS')
            cursor = self.db.cursor()
            try:
                norder += 1
                cursor.execute('''INSERT INTO FEEDS(URL, TITLE, IMAGE, NORDER)
     VALUES(?, ?, ?, ?)''', (url, title, image, norder))
                self.db.commit()
                ans = cursor.lastrowid
            except sqlite3.IntegrityError as e:
                print('---', e, '---')
            cursor.close()
        return ans

    def get_last_track_date(self, feed_id):
        feed = self.get_feed(feed_id)
        if feed is None:
            return None
        url = feed['url']
        print(url)
        last_date = None
        r = requests.get(url, verify=False)
        if r.status_code == 200:
            d = feedparser.parse(r.text)
            for index, entry in enumerate(d.entries):
                new_date = parse(entry.published).strftime('%Y%m%dT%H%M%S')
                print(new_date)
                if last_date is None or last_date < new_date:
                    last_date = new_date
        return last_date

    def add_tracks(self, feed_id, upperthan=None):
        feed = self.get_feed(feed_id)
        if feed is None:
            return
        url = feed['url']
        print('---', feed, '---')
        r = requests.get(url, verify=False)
        if r.status_code == 200:
            d = feedparser.parse(r.text)
            title = d.feed.title
            cursor = self.db.cursor()
            norder = self.get_max_norder('TRACKS')
            norder2 = self.get_max_norder_in_list(1)
            for index, entry in enumerate(d.entries):
                norder += 1
                norder2 += 1
                print(index)
                iden = entry.id
                date = parse(entry.published).strftime('%Y%m%dT%H%M%S')
                title = entry.title
                url = entry.enclosures[0]['url']
                filename = None
                duration = 0
                position = 0
                if upperthan is None or upperthan > date:
                    try:
                        cursor.execute('''INSERT INTO TRACKS(FEED_ID, IDEN,
 DATE, TITLE, URL, DURATION, POSITION, FILENAME, NORDER) VALUES(?, ?, ?, ?, ?,
 ?, ?, ?, ?)''',
                                       (feed_id, iden, date, title, url,
                                        duration, position, filename, norder))
                        track_id = cursor.lastrowid
                        cursor.execute('''INSERT INTO LIST(LIST_ID, TRACK_ID,
     POSITION, NORDER) VALUES(?, ?, ?, ?)''', (1, track_id, position, norder2))
                    except Exception as e:
                        print('---', e, '---')
            self.db.commit()
            cursor.close()
            return cursor.lastrowid
        return None

    def set_track_duration(self, id, duration):
        cursor = self.db.cursor()
        try:
            cursor.execute('''UPDATE TRACKS SET DURATION=? WHERE ID=?''',
                           (duration, id))
            self.db.commit()
        except Exception as e:
            print('---', e, '---')
        cursor.close()

    def set_track_position(self, id, position):
        cursor = self.db.cursor()
        try:
            cursor.execute('''UPDATE TRACKS SET POSITION=? WHERE ID=?''',
                           (position, id))
            self.db.commit()
        except Exception as e:
            print('---', e, '---')
        cursor.close()

    def set_track_position_in_list(self, id, list_id, position):
        cursor = self.db.cursor()
        try:
            cursor.execute(
                '''UPDATE LIST SET POSITION=? WHERE LIST_ID=? AND ID=?''',
                (position, list_id, id))
            self.db.commit()
        except Exception as e:
            print('---', e, '---')
        cursor.close()

    def set_track_listened(self, id):
        cursor = self.db.cursor()
        try:
            cursor.execute('''UPDATE TRACKS SET LISTENED=1 WHERE ID=?''',
                           (id,))
            self.db.commit()
        except Exception as e:
            print('---', e, '---')
        cursor.close()

    def set_track_no_listened(self, id):
        cursor = self.db.cursor()
        try:
            cursor.execute('''UPDATE TRACKS SET LISTENED=0 WHERE ID=?''',
                           (id,))
            self.db.commit()
        except Exception as e:
            print('---', e, '---')
        cursor.close()

    def is_track_listened(self, id):
        cursor = self.db.cursor()
        try:
            cursor.execute('''SELECT LISTENED FROM TRACKS WHERE ID=?''',
                           (id,))
            self.db.commit()
            ans = cursor.fetchone()
            if ans is not None:
                cursor.close()
                return (ans[0] is 1)
        except Exception as e:
            print('---', e, '---')
        cursor.close()
        return False

    def set_track_downloaded(self, id, filename):
        cursor = self.db.cursor()
        try:
            cursor.execute('''UPDATE TRACKS SET FILENAME=?, DOWNLOADED=1 WHERE
 ID=?''', (filename, id))
            self.db.commit()
        except Exception as e:
            print('---', e, '---')
        cursor.close()

    def set_track_no_downloaded(self, id):
        cursor = self.db.cursor()
        try:
            cursor.execute('''UPDATE TRACKS SET DOWNLOADED=0 WHERE ID=?''',
                           (id,))
            self.db.commit()
        except Exception as e:
            print('---', e, '---')
        cursor.close()

    def is_track_downloaded(self, id):
        cursor = self.db.cursor()
        try:
            cursor.execute('''SELECT DOWNLOADED FROM TRACKS WHERE ID=?''',
                           (id,))
            self.db.commit()
            ans = cursor.fetchone()
            if ans is not None:
                cursor.close()
                return (ans[0] is 1)
        except Exception as e:
            print('---', e, '---')
        cursor.close()
        return False

    def get_max_norder(self, table):
        cursor = self.db.cursor()
        cursor.execute('''SELECT max(NORDER) FROM {0}'''.format(table))
        ans = cursor.fetchone()[0]
        cursor.close()
        if ans is None:
            return 0
        return ans

    def get_max_norder_in_list(self, list_id):
        cursor = self.db.cursor()
        cursor.execute('''SELECT max(NORDER) FROM LIST WHERE LIST_ID=?''',
                       (list_id,))
        ans = cursor.fetchone()[0]
        cursor.close()
        if ans is None:
            return 0
        return ans

    def add_list(self, listname):
        norder = self.get_max_norder('LISTS')
        cursor = self.db.cursor()
        try:
            norder += 1
            cursor.execute('''INSERT INTO LISTS(NAME, NORDER) VALUES(?, ?)''',
                           (listname, norder))
            self.db.commit()
            cursor.close()
            return cursor.lastrowid
        except Exception as e:
            print('---', e, '---')
        cursor.close()
        return None

    def sort_list(self, elements):
        cursor = self.db.cursor()
        for element in elements:
            id, norder = element
            try:
                cursor.execute('''UPDATE LIST SET NORDER=? WHERE ID=?''',
                               (norder, id))
            except Exception as e:
                print('---', e, '---')
        self.db.commit()
        cursor.close()

    def add_track_to_list(self, list_id, track_id):
        norder = self.get_max_norder_in_list(list_id)
        cursor = self.db.cursor()
        try:
            norder += 1
            cursor.execute('''INSERT INTO LIST(LIST_ID, TRACK_ID, POSITION,
NORDER) VALUES(?, ?, ?, ?)''', (list_id, track_id, False, norder))
            self.db.commit()
            cursor.close()
            return cursor.lastrowid
        except Exception as e:
            print('---', e, '---')
        cursor.close()
        return None

    def removed_viewed_from_list(self, list_id):
        cursor = self.db.cursor()
        try:
            cursor.execute(
                '''DELETE FROM LIST WHERE LIST_ID=? AND POSITION=?''',
                (list_id, 100))
            self.db.commit()
        except Exception as e:
            print('---', e, '---')
        cursor.close()

    def get_feed_id(self, url):
        cursor = self.db.cursor()
        try:
            cursor.execute('SELECT ID FROM FEEDS WHERE URL=?', (url,))
            ans = cursor.fetchone()
            if ans is not None:
                cursor.close()
                return ans[0]
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        cursor.close()
        return None

    def get_feeds(self):
        ans = []
        cursor = self.db.cursor()
        try:
            cursor.execute('SELECT * FROM FEEDS')
            data = cursor.fetchall()
            cursor.close()
            for element in data:
                ans.append(Feed(element))
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        cursor.close()
        return ans

    def get_tracks_from_list(self, list_id):
        ans = []
        cursor = self.db.cursor()
        try:
            cursor.execute('SELECT * FROM TRACKS_LIST_VIEW WHERE LIST_ID=?',
                           (list_id,))
            data = cursor.fetchall()
            cursor.close()
            for element in data:
                track = Track()
                track.set_from_tracks_list_view(element)
                ans.append(track)
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        cursor.close()
        return ans

    def get_track_from_list(self, id):
        cursor = self.db.cursor()
        try:
            cursor.execute('SELECT * FROM TRACKS_LIST_VIEW WHERE ID=?', (id,))
            ans = cursor.fetchone()
            cursor.close()
            track = Track()
            track.set_from_tracks_list_view(ans)
            return track
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        cursor.close()
        return None

    def get_tracks_from_feed(self, feed_id, olderthan=None):
        ans = []
        cursor = self.db.cursor()
        try:
            if olderthan is None:
                cursor.execute('''SELECT * FROM TRACKS_FEED_VIEW WHERE
 FEED_ID=? ORDER BY DATE DESC''', (feed_id,))
            else:
                cursor.execute('''SELECT * FROM TRACKS_FEED_VIEW WHERE
 FEED_ID=? AND DATE>? ORDER BY DATE DESC''', (feed_id, olderthan,))
            data = cursor.fetchall()
            cursor.close()
            for element in data:
                track = Track()
                track.set_from_tracks_feed_view(element)
                ans.append(track)
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        cursor.close()
        return ans

    def get_track_from_feed(self, id):
        cursor = self.db.cursor()
        try:
            cursor.execute('SELECT * FROM TRACKS_FEED_VIEW WHERE ID=?', (id,))
            ans = cursor.fetchone()
            cursor.close()
            track = Track()
            track.set_from_tracks_feed_view(ans)
            return track
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        cursor.close()
        return None

    def get_last_track_from_feed(self, id):
        cursor = self.db.cursor()
        try:
            cursor.execute('''SELECT * FROM TRACKS_FEED_VIEW
 WHERE FEED_ID=? ORDER BY DATE DESC LIMIT 1;''', (id,))
            ans = cursor.fetchone()
            cursor.close()
            ans = Track(ans)
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        cursor.close()
        return ans

    def get_tracks(self):
        ans = []
        cursor = self.db.cursor()
        try:
            cursor.execute('SELECT * FROM TRACKS')
            data = cursor.fetchall()
            cursor.close()
            cursor.close()
            for element in data:
                ans.append(Track(element))
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        cursor.close()
        return ans

    def get_track(self, id):
        ans = None
        cursor = self.db.cursor()
        try:
            cursor.execute('SELECT * FROM TRACKS WHERE ID=?', (id,))
            ans = cursor.fetchone()
            cursor.close()
            ans = Track(ans)
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        cursor.close()
        return ans

    def get_feed(self, id):
        ans = None
        cursor = self.db.cursor()
        try:
            cursor.execute('SELECT * FROM FEEDS WHERE ID=?', (id,))
            ans = cursor.fetchone()
            cursor.close()
            ans = Feed(ans)
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        cursor.close()
        return ans


if __name__ == '__main__':
    import datetime
    print(datetime.datetime.strptime('20170524T125924', '%Y%m%dT%H%M%S'))
    create = False
    dbmanager = DBManager(create)
    if create is False:
        print(dbmanager.get_feeds())
        #print(dbmanager.get_tracks())
        print('---', dbmanager.get_last_track_from_feed(10), '---')
    else:
        dbmanager.add_feed('http://feeds.feedburner.com/ugeek')
        dbmanager.add_feed(
            'http://www.ivoox.com/salmorejo-geek_fg_f1206500_filtro_1.xml')
        for feed in dbmanager.get_feeds():
            dbmanager.add_tracks(feed['id'])
        dbmanager.add_list('Recent')

        dbmanager.set_track_downloaded(45, 'test')
        print(dbmanager.is_track_downloaded(45))
        print(dbmanager.is_track_downloaded(44))
        print(dbmanager.set_track_position(25, 50))
        print(dbmanager.set_track_position(30, 100))
        dbmanager.add_track_to_list(1, 44)
        dbmanager.set_track_position_in_list(44, 1, 100)
        dbmanager.removed_viewed_from_list(1)
        sortedlist = [[1, 2], [2, 1], [3, 5]]
        dbmanager.sort_list(sortedlist)

