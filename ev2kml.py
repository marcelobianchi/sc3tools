#!/usr/bin/env python
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

			print('<Style id="%s">' % ID, file = openfile)
			print('<LabelStyle>', file = openfile)
			print('<scale>0</scale>', file = openfile)
			print('</LabelStyle>', file = openfile)
			print('<IconStyle>', file = openfile)
			if color:
				print(' <color>%s</color>' % color, file = openfile)
			print(' <scale>%f</scale>' % scale, file = openfile)
			print(' <Icon>', file = openfile)
			print('  <href>http://maps.google.com/mapfiles/kml/shapes/donut.png</href>', file = openfile)
			print(' </Icon>', file = openfile)
			print('</IconStyle>', file = openfile)
			print('</Style>', file = openfile)
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

'''
KML Generators
'''
def openKML(openfile, options, styler):
	print('<?xml version="1.0" encoding="UTF-8"?>', file = openfile)
	print('<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">', file = openfile)
	print(' <Document>', file = openfile)

	if styler:
		styler.dump(openfile)

	print(' <Folder>', file = openfile)
	print('  <name>Earthquakes</name>', file = openfile)
	print('  <description><![CDATA[', file = openfile)
	print('  <p>SeisComP3 Event Extracter sc3xml2kml<br/>', file = openfile)
	print('  Depth Filter: %s/%s<br/>' % (options.mindep, options.maxdep), file = openfile)
	print('  Mag Filter: %s/%s<br/>' % (options.minmag, options.maxmag), file = openfile)
	print('  Picks Filter: %s</p>' % options.minarrival, file = openfile)
	print(']]>  </description>', file = openfile)

def ptKML(openfile, options, time, lon, lat, dep, mag, magt, desc, nar, style):

	if time == None: return
	if lon == None: return
	if lat == None: return

	print('  <Placemark>', file = openfile)
	if style:
		print('  <styleUrl>#%s</styleUrl>' % style, file = openfile)
	print('  <name>%s %s</name>' % (time, "(%s)" % desc if desc else ""), file = openfile)
	print('  <description><![CDATA[', file = openfile)
	if time != None:
		print('Origin time: %s<br/>' % time, file = openfile)
	print('Longitude: %.4f<br/>' % lon, file = openfile)
	print('Latitude: %.4f<br/>' % lat, file = openfile)
	if dep != None:
		print('Depth: %.0f (km)<br/>' % dep, file = openfile)
	if mag != None:
		print('Mag. %.2f %s<br/>' % (mag, magt), file = openfile)
	if nar != None:
		print('Number of arrivals: %d<br/>' % (nar), file = openfile)
	print(']]></description>', file = openfile)
	print('  <gx:TimeStamp><when>%s</when></gx:TimeStamp>' % (time), file = openfile)

	print('   <Point>', file = openfile)
	if options.skydepth:
		print('<altitudeMode>absolute</altitudeMode>', file = openfile)
	if dep:
		print('    <coordinates>%f,%f,%f</coordinates>' % (lon, lat, -1 * dep * 1000.0), file = openfile)
	else:
		print('    <coordinates>%f,%f,%f</coordinates>' % (lon, lat, 0.0), file = openfile)
	print('   </Point>', file = openfile)
	print('  </Placemark>', file = openfile)

def closeKML(openfile):
	print(' </Folder>', file = openfile)
	print(' </Document>', file = openfile)
	print(' </kml>', file = openfile)

'''
Data Reader
'''
def datafromxml(filename):
	data = None

	ar = IO.XMLArchive()
	ar.open(filename)
	obj = ar.readObject()
	ar.close()

	ep = DataModel.EventParameters.Cast(obj)

	if type(ep) == type(None):
		print ("File (%s) is no event, skipping." % filename, file = sys.stderr)
		return data

	if ep.eventCount == 0:
		print ("File (%s) has no events, skipping." % filename, file = sys.stderr)
		return data

	evt = ep.event(0)
	evt = DataModel.Event.Cast(evt)

	if type(evt) == type(None):
		print ("Cannot get event from file (%s), skipping." % filename, file = sys.stderr)
		return data

	if evt.preferredOriginID() == "":
		print ("No origin (%s), skipping." % filename, file = sys.stderr)
		return data

	if evt.preferredMagnitudeID() == "":
		print ("No magnitude (%s)" % filename, file = sys.stderr)

	ori = ep.findOrigin(evt.preferredOriginID())
	mag = ori.findMagnitude(evt.preferredMagnitudeID())

	data = { }
	data['time'] = ori.time().value().toString("%Y-%m-%dT%H:%M:%SZ")
	data['lat'] = ori.latitude().value()
	data['lon'] = ori.longitude().value()
	data['dep'] = ori.depth().value()
	data['arc'] = ori.arrivalCount()

	data['mag'] = None
	data['magt'] = None
	if type(mag) != type(None):
		data['mag'] = mag.magnitude().value()
		data['magt'] = mag.type()

	data['desc'] = None
	if evt.eventDescriptionCount() != 0:
		data['desc'] = evt.eventDescription(0).text()

	return data

'''
Scales
'''
def getsize(value, scale, power):
	if value == None:
		return 1.0

	v = int((math.pow(power,value)/2.0)*10*scale)/10
	if v < 0.2: v = 0.2

	return v

def getcolor(value,  scale):
	if value <= 10 * scale:
		return "FF152F9D"
	elif value < 35 * scale:
		return "FF15509D"
	elif value < 65 * scale:
		return "FF156D9D"
	elif value < 85 * scale:
		return "FF15889D"
	elif value < 120 * scale:
		return "FF159D9B"
	elif value < 300 * scale:
		return "FF128337"
	elif value < 500 * scale:
		return "FF0E5A13"
	elif value < 1000 * scale:
		return "FF222605"
	else:
		return "FF512B10"

'''
Basic
'''
def make_cmdline_parser():
	# Create the parser
	#
	parser = OptionParser(usage="%prog [options] <files>", version="1.0", add_help_option = True)

	parser.add_option("-c","--color", action="store_true", dest="usemagdep", help="Use magnitude for symbol size and depth to color circles", default=False)


	parser.add_option("--magpower", dest="magpower", help="Mag normalization power", default=1.4)
	parser.add_option("--magscale", dest="magscale", help="Mag normalization scale", default=1.0)
	parser.add_option("--depthscale", dest="depthscale", help="Depth scale, by default depth is between 0-1000km in 9 steps, making this number smaller than 1.0 reduces the maximum depth while keeping the number of colors", default=1.0)

	parser.add_option("--mindepth", type="string", dest="mindep", help="Filter events with depths smaller than MINDEP", default=None)
	parser.add_option("--maxdepth", type="string", dest="maxdep", help="Filter events with depths larger than MAXDEP", default=None)

	parser.add_option("--minmag", type="string", dest="minmag", help="Filter events with magnitude smaller than MINMAG", default=None)
	parser.add_option("--maxmag", type="string", dest="maxmag", help="Filter events with magnitude larger than MAXMAG", default=None)

	parser.add_option("--minarrival", type="string", dest="minarrival", help="Filter events with less than MINARRIVAL picks", default=None)
	parser.add_option("--maxarrival", type="string", dest="maxarrival", help="Filter events with more than MAXARRIVAL picks", default=None)

	parser.add_option("--flyover", action="store_true", dest="skydepth", help="Make earthquakes to fly above the surface", default=False)
	return parser

if __name__ == "__main__":
	parser = make_cmdline_parser()
	(options, args) = parser.parse_args()
	
	# Styler
	#
	styler = StyleFactory()

	try:
		float(options.magpower)
	except:
		print ("Bad mag power value.", file = sys.stderr)
		sys.exit(1)

	try:
		float(options.magscale)
	except:
		print ("Bad mag scale value.", file = sys.stderr)
		sys.exit(1)

	try:
		float(options.depthscale)
	except:
		print ("Bad depth scale value.", file = sys.stderr)
		sys.exit(1)

	# Loop each file
	#
	files = []
	for f in args:

		# Get data
		#
		data = datafromxml(f)
		if data == None: continue

		# Apply filters
		#
		if options.mindep and data['dep'] < float(options.mindep): continue
		if options.maxdep and data['dep'] > float(options.maxdep): continue

		if options.minmag and data['mag'] < float(options.minmag): continue
		if options.maxmag and data['mag'] > float(options.maxmag): continue

		if options.minarrival and data['arrivalc'] < int(options.minarrival): continue
		if options.maxarrival and data['arrivalc'] > int(options.maxarrival): continue

		# Find style
		#
		if options.usemagdep:
			style = styler.getstyle(size = getsize(data['mag'], float(options.magscale), float(options.magpower)),
									color = getcolor(data['dep'], float(options.depthscale)))
		else:
			style = styler.basicstyle()

		if options.skydepth:
			# Maximum earths eq depth is ~1000km
			data['dep'] = -0.5 * (1000.0 - data['dep'])

		data['style'] = style
		files.append(data)

	# Start KML
	#
	openKML(sys.stdout, options, styler)

	for data in files:
		# Write
		#
		ptKML(sys.stdout, options,
			data['time'],
			data['lon'],
			data['lat'],
			data['dep'],
			data['mag'],
			data['magt'],
			data['desc'],
			data['arc'],
			data['style'])

	# Finish
	#
	closeKML(sys.stdout)

	# END
	#
	sys.exit(0)
