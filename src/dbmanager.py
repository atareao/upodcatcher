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
import comun
import requests
import feedparser
import io
import os
import base64
from PIL import Image
from dateutil.parser import parse

SQLStartString = '''
DROP TABLE if exists FEEDS;
DROP TABLE if exists LISTS;
DROP TABLE if exists TRACKS;
DROP TABLE if exists LIST;
DROP VIEW if exists TRACKS_VIEW;
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
    FILENAME TEXT,
    NORDER INTEGER);
CREATE TABLE if not exists LIST (
    ID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
    LIST_ID INTEGER REFERENCES LISTS (ID) ON DELETE CASCADE,
    TRACK_ID INTEGER REFERENCES TRACKS (ID) ON DELETE CASCADE,
    POSITION INTEGER NOT NULL DEFAULT 0,
    NORDER INTEGER,
    UNIQUE (LIST_ID, TRACK_ID) ON CONFLICT IGNORE);
CREATE VIEW if not exists TRACKS_VIEW AS
    SELECT TRACKS.ID,
           FEEDS.TITLE AS PODCAST_NAME,
           FEEDS.IMAGE AS PODCAST_IMAGE,
           TRACKS.IDEN,
           TRACKS.DATE,
           TRACKS.TITLE,
           TRACKS.URL,
           TRACKS.DURATION,
           TRACKS.POSITION,
           TRACKS.FILENAME,
           TRACKS.NORDER
      FROM TRACKS
           LEFT JOIN
           FEEDS
     WHERE TRACKS.FEED_ID = FEEDS.ID;
INSERT OR IGNORE INTO LISTS (NAME, NORDER) VALUES ('Recent', 1);
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
        if not os.path.exists(comun.DATADIR):
            os.makedirs(comun.DATADIR)
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

    def add_feed(self, url):
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
                return cursor.lastrowid
            except sqlite3.IntegrityError as e:
                print('---', e, '---')
            cursor.close()
        return None

    def add_tracks(self, url):
        feed_id = self.get_feed_id(url)
        if feed_id is None:
            return
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
                try:
                    cursor.execute('''INSERT INTO TRACKS(FEED_ID, IDEN, DATE,
 TITLE, URL, DURATION, POSITION, FILENAME, NORDER) VALUES(?, ?, ?, ?, ?, ?, ?,
 ?, ?)''',
                                   (feed_id, iden, date, title, url, duration,
                                    position, filename, norder))
                    track_id = cursor.lastrowid
                    cursor.execute('''INSERT INTO LIST(LIST_ID, TRACK_ID,
 POSITION, NORDER) VALUES(?, ?, ?, ?)''', (1, track_id, position, norder2))
                except Exception as e:
                    print('---', e, '---')
            self.db.commit()
            cursor.close()
            return cursor.lastrowid
        return None

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
            cursor.execute('''UPDATE LIST SET POSITION=? WHERE LIST_ID=? AND ID=?''',
                           (position, list_id, id))
            self.db.commit()
        except Exception as e:
            print('---', e, '---')
        cursor.close()

    def set_track_downloaded(self, id, filename):
        cursor = self.db.cursor()
        try:
            cursor.execute('''UPDATE TRACKS SET FILENAME=? WHERE ID=?''',
                           (filename, id))
            self.db.commit()
        except Exception as e:
            print('---', e, '---')
        cursor.close()

    def set_track_no_downloaded(self, id):
        self.set_track_downloaded(id, None)

    def is_track_downloaded(self, id):
        cursor = self.db.cursor()
        try:
            cursor.execute('''SELECT FILENAME FROM TRACKS WHERE ID=?''',
                           (id,))
            self.db.commit()
            ans = cursor.fetchone()
            if ans is not None:
                cursor.close()
                return (ans[0] is not None)
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
            cursor.execute('''DELETE FROM LIST WHERE LIST_ID=? AND POSITION=?''',
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
        cursor = self.db.cursor()
        try:
            cursor.execute('SELECT * FROM FEEDS')
            ans = cursor.fetchall()
            cursor.close()
            return ans
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        cursor.close()
        return []

    def get_tracks(self):
        cursor = self.db.cursor()
        try:
            cursor.execute('SELECT * FROM TRACKS_VIEW')
            ans = cursor.fetchall()
            cursor.close()
            return ans
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        cursor.close()
        return []

    def get_track(self, id):
        cursor = self.db.cursor()
        try:
            cursor.execute('SELECT * FROM TRACKS_VIEW WHERE ID=?', (id,))
            ans = cursor.fetchone()
            cursor.close()
            return ans
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        cursor.close()
        return None


if __name__ == '__main__':
    create = True
    dbmanager = DBManager(create)
    if create is False:
        print(dbmanager.get_feeds())
        print(dbmanager.get_tracks())
    else:
        '''
        dbmanager.add_feed('http://feeds.feedburner.com/ugeek')
        dbmanager.add_feed('http://www.ivoox.com/salmorejo-geek_fg_f1206500_filtro_1.xml')
        print(dbmanager.get_feed_id('http://feeds.feedburner.com/ugeek'))
        dbmanager.add_tracks('http://feeds.feedburner.com/ugeek')
        dbmanager.add_tracks('http://www.ivoox.com/salmorejo-geek_fg_f1206500_filtro_1.xml')
        dbmanager.add_list('Recent')
        '''
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

