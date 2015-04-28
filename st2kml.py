#!/usr/bin/python
# -*- coding: utf-8 -*-
#
################################################################################
#                                                                              #
#   SeisComp3 XML to KML converter                                             #
#   Copyright (C) 2015  Marcelo Belentani de Bianchi                           #
#                                                                              #
#   This program is free software; you can redistribute it and/or modify       #
#   it under the terms of the GNU General Public License as published by       #
#   the Free Software Foundation; either version 2 of the License, or          #
#   (at your option) any later version.                                        #
#                                                                              #
#   This program is distributed in the hope that it will be useful,            #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of             #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              #
#   GNU General Public License for more details.                               #
#                                                                              #
#   You should have received a copy of the GNU General Public License along    #
#   with this program; if not, write to the Free Software Foundation, Inc.,    #
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.                #
#                                                                              #
#### 2015-02-26 ################################################################
#

import sys, hashlib, math
from seiscomp3 import IO, DataModel
from optparse import OptionParser
import seiscomp3
import code

'''
Style Factory
'''
class StyleFactory(object):
    def __init__(self):
        self.styles = {}

    def dump(self, openfile):
        for ID in self.styles:
            color = self.styles[ID]['color']
            scale = self.styles[ID]['size']

            print >>openfile,'<Style id="%s">' % ID
            print >>openfile,'<LabelStyle>'
            print >>openfile,'<scale>0</scale>'
            print >>openfile,'</LabelStyle>'
            print >>openfile,'<IconStyle>'
            if color:
                print >>openfile,' <color>%s</color>' % color
            print >>openfile,' <scale>%f</scale>' % scale
            print >>openfile,' <Icon>'
            print >>openfile,'  <href>http://maps.google.com/mapfiles/kml/shapes/triangle.png</href>'
            print >>openfile,' </Icon>'
            print >>openfile,'</IconStyle>'
            print >>openfile,'</Style>'
        return

    def basicstyle(self):
        if not 'basic' in self.styles:
            self.styles['basic'] = { }
            self.styles['basic']['color'] = 'cc0000ff'
            self.styles['basic']['size']  = 1.0
        return "basic"

    def getstyle(self, size, color):
        sh1 = "S_%s" %  hashlib.sha1("%.2f-%s" %  (size, color)).hexdigest()
        if sh1 in self.styles:
            return sh1
        self.styles[sh1] = { }
        self.styles[sh1]['color'] = color
        self.styles[sh1]['size'] = size

        return sh1

def newFolder(openfile, name):
    print >>openfile,' <Folder>'
    print >>openfile,'  <name>%s</name>' % name
#     print >>openfile,'  <description><![CDATA['
#     print >>openfile,'  <p>SeisComP3 Station Extracter st2kml<br/>'
#     print >>openfile,']]>  </description>'

'''
KML Generators
'''
def openKML(openfile, options, styler):
    print >>openfile,'<?xml version="1.0" encoding="UTF-8"?>'
    print >>openfile,'<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">'
    print >>openfile,' <Document>'

    if styler:
        styler.dump(openfile)

def ptKML(openfile, options, code, channels, start, end, lon, lat, ele, desc, style):
    if start == None: return
    if lon == None: return
    if lat == None: return

    print >>openfile,'  <Placemark>'
    if style:
        print >>openfile,'  <styleUrl>#%s</styleUrl>' % style

    print >>openfile,'  <name>%s</name>' % (code)
    print >>openfile,'  <description><![CDATA['

    print >>openfile,"<pre>Description: %s" % desc
    print >>openfile,"Locations and Channels Names:"
    print >>openfile,"(SEED Standard Naming)"
    print >>openfile,"  %s" % channels

    print >>openfile,"Operation Time:"
    print >>openfile,'Start: %s End: %s' % (start, "--" if end is None else end)

    print >>openfile,"Station Location:"
    print >>openfile,' Longitude: %+09.4f' % lon
    print >>openfile,' Latitude:  %+09.4f' % lat
    print >>openfile,' Elevation: %6.1f (m)' % ele

    print >>openfile,'</pre>]]></description>'

    print >>openfile,'  <TimeSpan>'
    print >>openfile,'    <begin>%s</begin>' % (start)
    if end:
        print >>openfile,'    <end>%s</end>' % (end)
    print >>openfile,'  </TimeSpan>'

    print >>openfile,'   <Point>'
    print >>openfile,'    <coordinates>%f,%f,%f</coordinates>' % (lon, lat, 0.0)
    print >>openfile,'   </Point>'
    print >>openfile,'  </Placemark>'

def closeFolder(openfile):
    print >>openfile,' </Folder>'

def closeKML(openfile):
    print >>openfile,' </Document>'
    print >>openfile,' </kml>'

'''
Scales
'''
def getsize():
    return 2.0

def getcolor(network, open):
    if network == "BR":
        return "FF152F9D"
    elif network == "NB":
        return "FF15509D"
    elif network == "ON":
        return "FF156D9D"
    elif network == "BL":
        return "FF512B10"

    return "00000000"

def datafromxml(filename):
    ar = IO.XMLArchive()
    ar.open(filename)
    obj = ar.readObject()
    ar.close()

    inv = DataModel.Inventory.Cast(obj)

    if type(inv) == type(None):
        print >>sys.stderr,"File (%s) is no event, skipping." % filename
        return None

    return inv

def collect(sta):
    codes = []

    for ll in range(0,sta.sensorLocationCount()):
        loc = sta.sensorLocation(ll)
        for cc in range(0,loc.streamCount()):
            cha = loc.stream(cc)
            codes.append("%s.%s" % ("--" if loc.code() == "" else loc.code(), cha.code()))

    codes.sort(reverse = True)
    return ",".join(codes)

'''
Basic
'''
def make_cmdline_parser():
    # Create the parser
    #
    parser = OptionParser(usage="%prog [options] <files>", version="1.0", add_help_option = True)
    return parser

if __name__ == "__main__":
    parser = make_cmdline_parser()
    (options, args) = parser.parse_args()
    
    # Styler
    #
    styler = StyleFactory()

    # Loop each file
    #
    files = { }
    for f in args:

        # Get data
        #
        inv = datafromxml(f)
        if type(inv) == type(None): continue

        for nn in range(0,inv.networkCount()):
            net = inv.network(nn)
            for ss in range(0, net.stationCount()):
                sta = net.station(ss)

                try:
                    end = sta.end().toString("%Y-%m-%dT%H:%M:%SZ")
                except seiscomp3.Core.ValueException:
                    end = None
                
                data = { }
                code = "%s.%s" % (net.code(), sta.code())
                data['code'] = code
                data['desc'] = sta.description()
                data['start'] = sta.start().toString("%Y-%m-%dT%H:%M:%SZ")
                data['end'] = end
                data['channels'] = collect(sta)
                data['latitude'] = sta.latitude()
                data['longitude'] = sta.longitude()
                data['elevation'] = sta.elevation()
                
                # Find style
                #
                style = styler.getstyle(size = getsize(),
                                        color = getcolor(net.code(), net.start()))
                data['style'] = style

                if code in files:
                    if data['end'] is None and files[code]['end'] is not None:
                        files[code] = data
                else:
                    files[code] = data

    # Start KML
    #
    openKML(sys.stdout, options, styler)

    newFolder(sys.stdout, "Stations Already closed")
    for (k,data) in files.iteritems():
        if data['end'] is None: continue
        ptKML(sys.stdout, options,
            data['code'],
            data['channels'],
            data['start'],
            data['end'],
            data['longitude'],
            data['latitude'],
            data['elevation'],
            data['desc'],
            data['style'])
    closeFolder(sys.stdout)

    newFolder(sys.stdout, "Stations in Operation")
    for (k,data) in files.iteritems():
        if data['end'] is not None: continue
        ptKML(sys.stdout, options,
            data['code'],
            data['channels'],
            data['start'],
            data['end'],
            data['longitude'],
            data['latitude'],
            data['elevation'],
            data['desc'],
            data['style'])
    closeFolder(sys.stdout)

    # Finish
    #
    closeKML(sys.stdout)

    # END
    #
    sys.exit(0)
