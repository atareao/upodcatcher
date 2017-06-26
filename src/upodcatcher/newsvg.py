#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# newsvg.py
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
    gi.require_version('GdkPixbuf', '2.0')
    gi.require_version('Gdk', '3.0')
except Exception as e:
    print(e)
    exit(1)
from gi.repository import GdkPixbuf
from gi.repository import Gdk
import cairo


SVG = '''
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:cc="http://creativecommons.org/ns#"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns="http://www.w3.org/2000/svg"
   id="svg8"
   version="1.1"
   viewBox="0 0 31.749999 31.750001"
   height="120"
   width="120">
  <defs
     id="defs2" />
  <metadata
     id="metadata5">
    <rdf:RDF>
      <cc:Work
         rdf:about="">
        <dc:format>image/svg+xml</dc:format>
        <dc:type
           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />
        <dc:title></dc:title>
      </cc:Work>
    </rdf:RDF>
  </metadata>
  <g
     transform="translate(0,-265.24998)"
     id="layer1">
    <rect
       y="289.06247"
       x="0"
       height="7.9375"
       width="31.75"
       id="rect4485"
       style="fill:#ffffff;fill-opacity:0.47058824;stroke:none;stroke-width:0.76499999;stroke-miterlimit:4;stroke-dasharray:none" />
    <text
       id="text4489"
       y="295.5513"
       x="15.759589"
       style="font-style:normal;font-variant:normal;font-weight:normal;font-stretch:normal;font-size:10.58333302px;line-height:1.25;font-family:'Open Sans';-inkscape-font-specification:'Open Sans';text-align:center;letter-spacing:0px;word-spacing:0px;text-anchor:middle;fill:#000000;fill-opacity:1;stroke:none;stroke-width:0.26458332"
       xml:space="preserve"><tspan
         style="font-size:7.05555534px;text-align:center;text-anchor:middle;stroke-width:0.26458332"
         y="295.5513"
         x="15.759589"
         id="tspan4487">$$TEXT$$</tspan></text>
  </g>
</svg>

'''


def get_pixbuf(text):
    svg = SVG.replace('$$TEXT$$', text)
    loader = GdkPixbuf.PixbufLoader()
    loader.write(svg.encode())
    loader.close()
    return loader.get_pixbuf()


def put_text(pixbuf, text, size=30):
    print(3)
    width = pixbuf.get_width()
    height = pixbuf.get_height()
    imageSurface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    context = cairo.Context(imageSurface)

    Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
    context.paint()

    context.rectangle(0, height - size, width, size)
    context.set_source_rgba(1, 1, 1, 0.7)
    context.fill()

    context.set_font_size(size - (size / 10) * 2)
    context.set_source_rgba(0, 0, 0, 1)
    xbearing, ybearing, font_width, font_height, xadvance, yadvance =\
        context.text_extents(text)
    y = height - (size - font_height) / 2
    x = (width - font_width) / 2
    context.move_to(x, y)
    context.show_text(text)

    result = Gdk.pixbuf_get_from_surface(imageSurface, 0, 0,
                                         width,
                                         height)
    return result


if __name__ == '__main__':
    import comun
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(comun.PLAY_ICON, 120, 120)
    pixbuf = put_text(pixbuf, '123')
    pixbuf.savev('/home/lorenzo/Escritorio/sample.png', 'png', [], [])
