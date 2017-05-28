#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# opmlparser.py
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

from xml.etree import ElementTree
from datetime import datetime
from urllib.parse import urlparse
import getpass

FORMAT = '%a, %d %b %Y %X'


def extract_rss_urls_from_opml(anstring):
    urls = []
    tree = ElementTree.fromstring(anstring)
    for node in tree.findall('.//outline'):
        url = node.attrib.get('xmlUrl')
        if url:
            urls.append(url)
    return urls


def create_element(root, tag, attrs={}, text=None):
    element = ElementTree.Element(tag)
    for key in attrs.keys():
        element.set(key, attrs[key])
    if text is not None:
        element.text = text
    root.append(element)
    return element


def create_opml_from_urls(urls):
    top = ElementTree.Element('opml')
    top.set('version', '2.0')
    head = create_element(top, 'head')
    create_element(head, 'title', text='suscriptions.opml')
    create_element(head, 'dateCreated', text=datetime.now().strftime(FORMAT))
    create_element(head, 'dateModified', text=datetime.now().strftime(FORMAT))
    create_element(head, 'ownerName', text=getpass.getuser())
    create_element(head, 'ownerEmail')
    body = create_element(top, 'body')
    for url in urls:
        parsed_uri = urlparse(url)
        domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
        attrs = {}
        attrs['text'] = ''
        attrs['description'] = ''
        attrs['htmlUrl'] = domain
        attrs['language'] = ''
        attrs['title'] = ''
        attrs['type'] = 'rss'
        attrs['version'] = 'RSS2'
        attrs['xmlUrl'] = url
        create_element(body, 'outline', attrs=attrs)
    ans = ElementTree.tostring(top).decode('utf-8')
    ans = '<?xml version="1.0" encoding="utf-8"?>' + ans
    return ans


if __name__ == '__main__':
    from utils import read_remote_file
    ans = read_remote_file(
        'http://hosting.opml.org/dave/spec/subscriptionList.opml')
    urls = extract_rss_urls_from_opml(ans)

    print(urls)

    print(create_opml_from_urls(urls))
