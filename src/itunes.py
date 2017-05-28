#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# itunes.py
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

import requests
import locale
from urllib.parse import urljoin
from upod_classes import Feed
from dbmanager import create_base64

BASE_URL = 'http://itunes.apple.com/'
GENRES_PATH = '/WebObjects/MZStoreServices.woa/ws/genres'
LOOKUP_PATH = '/lookup'
SEARCH_PATH = '/search'


class PodcastClient(object):

    def __init__(self):
        self.__base_url = BASE_URL
        self.__timeout = 5
        self.__session = requests.Session()
        self.__genres = {}

    def search(self, term, media=None, entity=None, attribute=None, limit=None,
               explicit=None, genre_id=None):
        country = locale.getlocale()[0][:2].upper()
        result = self.__request(urljoin(self.__base_url, SEARCH_PATH),
                                params={
            'term': term,
            'media': media,
            'entity': entity,
            'attribute': attribute,
            'limit': limit,
            'country': country,
            # apparently only lowercase will work, contrary to iTunes specs
            'explicit': (explicit.lower() if explicit else None),
            # undocumented, and apparently not really working as expected
            'genreId': genre_id,
            'kind': 'podcast'
        })
        ans = result.get('results', [])
        result = []
        if len(ans) > 0:
            for index, element in enumerate(ans):
                try:
                    feed = Feed()
                    feed['id'] = index
                    feed['url'] = element['feedUrl']
                    feed['name'] = element['trackName']
                    feed['image'] = create_base64(element['artworkUrl100'])
                    feed['norder'] = index
                    result.append(feed)
                except Exception as e:
                    print(e)
        return result

    def __request(self, url, **kwargs):
        response = self.__session.get(url, timeout=self.__timeout, **kwargs)
        response.raise_for_status()
        return response.json()


if __name__ == '__main__':
    import pprint
    itp = PodcastClient()
    pprint.pprint(itp.search('ugeek', limit=20))
