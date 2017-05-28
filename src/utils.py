#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# utils.py
#
# This file is part of uPodcatcher
#
# Copyright (C) 2014
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
import gi
try:
    gi.require_version('GdkPixbuf', '2.0')
except Exception as e:
    print(e)
    exit(1)
from gi.repository import GdkPixbuf
import base64
import comun

NOIMAGE = GdkPixbuf.Pixbuf.new_from_file_at_size(comun.NOIMAGE_ICON, 128, 128)


def download_file(url, local_filename):
    # NOTE the stream=True parameter
    try:
        r = requests.get(url, stream=True)
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(e)
    return False


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
