#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# upod_classes.py
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


class Base(dict):

    def __init__(self, data=None):
        dict.__init__(self)
        if data is None:
            self.set_default()
        else:
            self.set(data)

    def set_default(self):
        pass

    def set(self, data):
        pass

    def __eq__(self, other):
        return self['id'] == other['id']

    def __ne__(self, other):
        return self['id'] != other['id']

    def __lt__(self, other):
        return self['norder'] < other['norder']

    def __le__(self, other):
        return self['norder'] <= other['norder']

    def __gt__(self, other):
        return other['norder'] < self['norder']

    def __ge__(self, other):
        return other['norder'] <= self['norder']

    def __str__(self):
        ans = []
        for key in self.keys():
            ans.append('{0}: {1}\n'.format(key, self[key]))
        return ''.join(ans)


class Feed(Base):

    def __init__(self, data=None):
        Base.__init__(self, data)

    def set_default(self):
        self['id'] = -1
        self['url'] = None
        self['title'] = None
        self['image'] = None
        self['link'] = ''
        self['description'] = ''
        self['norder'] = -1

    def set(self, data):
        self['id'] = data[0]
        self['url'] = data[1]
        self['title'] = data[2]
        self['image'] = data[3]
        self['link'] = data[4]
        self['description'] = data[5]
        self['norder'] = data[6]


class List(Base):

    def __init__(self, data=None):
        Base.__init__(self, data)

    def set_default(self):
        self['id'] = -1
        self['name'] = None
        self['norder'] = -1

    def set(self, data):
        self['id'] = data[0]
        self['name'] = data[1]
        self['norder'] = data[2]


class Track(Base):

    def __init__(self, data=None):
        Base.__init__(self, data)

    def set_default(self):
        self['id'] = -1
        self['feed_id'] = -1
        self['iden'] = None
        self['date'] = None
        self['title'] = None
        self['url'] = None
        self['link'] = ''
        self['description'] = ''
        self['duration'] = -1
        self['position'] = -1
        self['listened'] = 0
        self['downloaded'] = 0
        self['filename'] = None
        self['norder'] = -1
        self['feed_name'] = None
        self['feed_image'] = None
        self['list_id'] = -1

    def set(self, data):
        self['id'] = data[0]
        self['feed_id'] = data[1]
        self['iden'] = data[2]
        self['date'] = data[3]
        self['title'] = data[4]
        self['url'] = data[5]
        self['link'] = data[6]
        self['description'] = data[7]
        self['duration'] = data[8]
        self['position'] = data[9]
        self['downloaded'] = data[10]
        self['listened'] = data[11]
        self['filename'] = data[12]
        self['norder'] = data[13]

    def set_from_tracks_feed_view(self, data):
        self.set(data)
        self['feed_name'] = data[14]
        self['feed_image'] = data[15]

    def set_from_tracks_list_view(self, data):
        self.set_from_tracks_feed_view(data)
        self['list_id'] = data[16]


if __name__ == '__main__':
    feed1 = Feed()
    feed2 = Feed()
    feed1['norder'] = 2
    feed2['norder'] = 1
    print(feed1 == feed2)
    feed2['id'] = 25
    print(feed1 == feed2)
    print(feed1 != feed2)
    print(feed1 < feed2)
    print(feed1)
    print(feed2)
    alist = [feed1, feed2]
    print(alist)
    alist.sort()
    print(alist)
