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
    VIEWED BOOLEAN NOT NULL DEFAULT FALSE,
    DOWNLOADED BOOLEAN NOT NULL DEFAULT FALSE,
    NORDER INTEGER);
CREATE TABLE if not exists LIST (
    ID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
    LIST_ID INTEGER REFERENCES LISTS (ID) ON DELETE CASCADE,
    TRACK_ID INTEGER REFERENCES TRACKS (ID) ON DELETE CASCADE,
    VIEWED BOOLEAN DEFAULT FALSE,
    NORDER INTEGER);
CREATE VIEW if not exists TRACKS_VIEW AS
    SELECT TRACKS.ID,
           FEEDS.TITLE AS PODCAST_NAME,
           FEEDS.IMAGE AS PODCAST_IMAGE,
           TRACKS.IDEN,
           TRACKS.DATE,
           TRACKS.TITLE,
           TRACKS.URL,
           TRACKS.VIEWED,
           TRACKS.DOWNLOADED,
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
        self.db = sqlite3.connect(comun.DATABASE)
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
                viewed = False
                downloaded = False
                try:
                    cursor.execute('''INSERT INTO TRACKS(FEED_ID, IDEN, DATE,
 TITLE, URL, VIEWED, DOWNLOADED, NORDER) VALUES(?, ?, ?, ?, ?, ?, ?, ?)''',
                                   (feed_id, iden, date, title, url, viewed,
                                    downloaded, norder))
                    track_id = cursor.lastrowid
                    cursor.execute('''INSERT INTO LIST(LIST_ID, TRACK_ID,
 VIEWED, NORDER) VALUES(?, ?, ?, ?)''', (1, track_id, viewed, norder2))
                except Exception as e:
                    print('---', e, '---')
            self.db.commit()
            return cursor.lastrowid
        return None

    def set_track_downloaded(self, id, downloaded=True):
        cursor = self.db.cursor()
        try:
            cursor.execute('''UPDATE TRACKS SET DOWNLOADED=? WHERE ID=?''',
                           (downloaded, id))
            self.db.commit()
        except Exception as e:
            print('---', e, '---')

    def is_track_downloaded(self, id):
        cursor = self.db.cursor()
        try:
            cursor.execute('''SELECT DOWNLOADED FROM TRACKS WHERE ID=?''',
                           (id,))
            self.db.commit()
            ans = cursor.fetchone()
            if ans is not None:
                return ans[0] == 1
        except Exception as e:
            print('---', e, '---')
        return False

    def get_max_norder(self, table):
        cursor = self.db.cursor()
        cursor.execute('''SELECT max(NORDER) FROM {0}'''.format(table))
        ans = cursor.fetchone()[0]
        if ans is None:
            return 0
        return ans

    def get_max_norder_in_list(self, list_id):
        cursor = self.db.cursor()
        cursor.execute('''SELECT max(NORDER) FROM LIST WHERE LIST_ID=?''',
                       (list_id,))
        ans = cursor.fetchone()[0]
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
            return cursor.lastrowid
        except Exception as e:
            print('---', e, '---')
        return None

    def set_track_viewed(self, id, viewed=True):
        cursor = self.db.cursor()
        try:
            cursor.execute('''UPDATE LIST SET VIEWED=? WHERE ID=?''',
                           (viewed, id))
            self.db.commit()
        except Exception as e:
            print('---', e, '---')

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

    def add_track_to_list(self, list_id, track_id):
        norder = self.get_max_norder(list_id)
        cursor = self.db.cursor()
        try:
            norder += 1
            cursor.execute('''INSERT INTO LIST(LIST_ID, TRACK_ID, VIEWED,
NORDER) VALUES(?, ?, ?, ?)''', (list_id, track_id, False, norder))
            self.db.commit()
            return cursor.lastrowid
        except Exception as e:
            print('---', e, '---')
        return None

    def removed_viewed_from_list(self, list_id):
        cursor = self.db.cursor()
        try:
            cursor.execute('''DELETE FROM LIST WHERE LIST_ID=? AND VIEWED=?''',
                           (list_id, True))
            self.db.commit()
        except Exception as e:
            print('---', e, '---')

    def get_feed_id(self, url):
        cursor = self.db.cursor()
        try:
            cursor.execute('SELECT ID FROM FEEDS WHERE URL=?', (url,))
            ans = cursor.fetchone()
            if ans is not None:
                return ans[0]
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        return None

    def get_feeds(self):
        cursor = self.db.cursor()
        try:
            cursor.execute('SELECT * FROM FEEDS')
            return cursor.fetchall()
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        return []

    def get_tracks(self):
        cursor = self.db.cursor()
        try:
            cursor.execute('SELECT * FROM TRACKS_VIEW')
            return cursor.fetchall()
        except (sqlite3.IntegrityError, AttributeError) as e:
            print('---', e, '---')
        return []


if __name__ == '__main__':
    create = False
    dbmanager = DBManager(create)
    if create is False:
        print(dbmanager.get_feeds())
        print(dbmanager.get_tracks())
    else:
        dbmanager.add_feed('http://feeds.feedburner.com/ugeek')
        print(dbmanager.get_feed_id('http://feeds.feedburner.com/ugeek'))
        dbmanager.add_tracks('http://feeds.feedburner.com/ugeek')
        dbmanager.add_list('Recent')
        dbmanager.set_track_downloaded(45, True)
        print(dbmanager.is_track_downloaded(45))
        print(dbmanager.is_track_downloaded(44))
        print(dbmanager.set_track_viewed(25))
        dbmanager.removed_viewed_from_list(1)
        sortedlist = [[1, 2], [2, 1], [3, 5]]
        dbmanager.sort_list(sortedlist)

