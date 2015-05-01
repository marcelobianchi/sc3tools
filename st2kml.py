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
import datetime, re

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

def ptKML(openfile, options, code, channels, start, end, lon, lat, ele, desc, rmk, sensor, dtl, style):
    if start == None: return
    if lon == None: return
    if lat == None: return

    print >>openfile,'  <Placemark>'
    if style:
        print >>openfile,'  <styleUrl>#%s</styleUrl>' % style

    print >>openfile,'  <name>%s</name>' % (code.split(".")[1])
    print >>openfile,'  <description><![CDATA['

    print >>openfile,"<pre>"
    
    print >>openfile,"<b>Description:</b> %s" % desc
    
    print >>openfile,""
    print >>openfile,"<b>Network:</b> %s" % (code.split(".")[0])
    
    print >>openfile,""
    print >>openfile,"<b>Locations and Channels Names:</b>"
    print >>openfile,"(SEED Standard Naming)"

    for chunk in re.findall('.{21}',channels) if len(channels) > 21 else [channels]:
        print >>openfile,"  %s" % chunk
    print >>openfile,""

    print >>openfile,"<b>Operation Time:</b>"
    print >>openfile,'  Start: %s' % start
    print >>openfile,'    End: %s' % ("--" if end is None else end)

    print >>openfile,""
    print >>openfile,"<b>Station Location:</b>"
    print >>openfile,'  Longitude: %+09.4f' % lon
    print >>openfile,'  Latitude:  %+09.4f' % lat
    print >>openfile,'  Elevation: %6.1f (m)' % ele

    method = {
     None: "Unset",
     '-': "Offline",
     "S": "Satelite",
     "W": "Wireless Lan Provider",
     "2G": "Mobile Phone Network"
    }

    online = {
         None: "Unknow",
         '-': "Offline",
         "S": "Online",
         "W": "Online",
         "2G": "Online"
    }

    print >>openfile,""
    print >>openfile,"<b>Station Transmission:</b>"
    if end is None:
        print >>openfile,"  Status is %s" % online[rmk]
        if online[rmk] == "Online":
            print >>openfile,"  Method: %s" % method[rmk]
    else:
        print >>openfile,"  Status is closed."

    print >>openfile,""
    print >>openfile,"<b>Instruments in Station:</b>"
    print >>openfile,"  %s ; %s" % ("--" if sensor is None else sensor, "--" if dtl is None else dtl)
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
    return 1.5

def getcolor(network, open):
    #cusp=0/46/166    # BL # 002ea6
    #cunb=44/124/17   # BR # 23640e
    #con=232/113/21   # ON # e87115
    #cufrn=222/232/21 # NB # dee815
    #6cbd50 -> 50BD6C
    if network == "BR":
        return "FF50BD6C" if open == "true" else "CC50BD6C" 
    elif network == "NB":
        return "FF15E8DE" if open == "true" else "CC15E8DE"
    elif network == "ON":
        return "FF1571E8" if open == "true" else "CC1571E8"
    elif network == "BL":
        return "FFA62E00" if open == "true" else "CCA62E00"

    return "FFDDDDDD" if open == "true" else "CCDDDDDD"

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
#             sensor=sta.network().inventory().findSensor(cha.sensor())
#             print "MA='%s' MO='%s' DS='%s' %s" % (sensor.manufacturer(),sensor.model(),sensor.description(),sensor.name())

    codes.sort(reverse = True)
    return ",".join(codes)

'''
Basic
'''
def make_cmdline_parser():
    # Create the parser
    #
    parser = OptionParser(usage="%prog [options] <files>", version="1.0", add_help_option = True)
    parser.add_option("-f", "--filter", type="string", dest="filter", help="Network list to filter (BL,BR)", default=None)
    parser.add_option("-o","--output", type="string", dest="output", help="Output filename", default=None)

    return parser

if __name__ == "__main__":
    parser = make_cmdline_parser()
    (options, args) = parser.parse_args()

    fio = sys.stdout

    if options.output:
        fio = open(options.output,"w")

    # Styler
    #
    styler = StyleFactory()

    # Loop each file
    #
    records = {
               'true' : { },
               'false': { }}

    if options.filter:
        options.filter = options.filter.split(",")

    for f in args:
        print >>sys.stderr,"Processing file: %s" % f
        # Get data
        #
        inv = datafromxml(f)
        if type(inv) == type(None): continue

        for nn in range(0,inv.networkCount()):
            net = inv.network(nn)
            if options.filter and net.code() not in options.filter: continue
            for ss in range(0, net.stationCount()):
                sta = net.station(ss)

                try:
                    end = sta.end()
                    d = datetime.datetime.strptime(end.toString("%Y-%m-%d %H:%M:%SZ"), "%Y-%m-%d %H:%M:%SZ")
                    open = "true" if d > datetime.datetime.now() else "false"
                    end = end.toString("%Y-%m-%dT%H:%M:%SZ")
                except seiscomp3.Core.ValueException:
                    end = None
                    open = "true"
                
                try:
                    rmk = sta.remark().content()
                    if rmk.find(";") != -1:
                        rmk = rmk.split(";")
                        dtl=rmk[2]
                        sen=rmk[1]
                        rmk=rmk[0]
                except seiscomp3.Core.ValueException:
                    rmk = None
                    dtl = None
                    sen = None
                
                data = { }
                code = "%s.%s" % (net.code(), sta.code())
                data['code'] = code
                data['desc'] = sta.description()
                data['remark'] = rmk
                data['sensor'] = sen
                data['dtl'] = dtl
                data['start'] = sta.start().toString("%Y-%m-%dT%H:%M:%SZ")
                data['end'] = end
                data['open'] = open
                data['channels'] = collect(sta)
                data['latitude'] = sta.latitude()
                data['longitude'] = sta.longitude()
                data['elevation'] = sta.elevation()
                
                # Find style
                #
                style = styler.getstyle(size = getsize(),
                                        color = getcolor(net.code(), open))
                data['style'] = style

                if net.code() not in records[open]:
                    records[open][net.code()] = { }

                where = records[open][net.code()]

                if code in where:
                    if data['end'] is None and where[code]['open'] is "false":
                        print >>sys.stderr,"Over-write."
                        where[code] = data
                else:
                    where[code] = data

    # Start KML
    #
    openKML(fio, options, styler)

    for (k,g) in records.iteritems():
        if k == "false":
            newFolder(fio, "Stations Already closed")
        else:
            newFolder(fio, "Stations in Operation")

        nkeys = g.keys()
        nkeys.sort()
        for n in nkeys:
            net = g[n]
            newFolder(fio, "%s network (%d stations)" % (n,len(net)))

            skeys = net.keys()
            skeys.sort()
            for s in skeys:
                data = net[s]
                ptKML(fio, options,
                    data['code'],
                    data['channels'],
                    data['start'],
                    data['end'],
                    data['longitude'],
                    data['latitude'],
                    data['elevation'],
                    data['desc'],
                    data['remark'],
                    data['sensor'],
                    data['dtl'],
                    data['style'])
            closeFolder(fio)
        closeFolder(fio)
 
    # Finish
    #
    closeKML(fio)

    if fio != sys.stdout:
        fio.close()

    # END
    #
    sys.exit(0)
