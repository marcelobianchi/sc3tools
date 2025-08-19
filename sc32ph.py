#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
################################################################################
#                                                                              #
#   SeisComp3 XML to hypoDD converter                                          #
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
#### 2015-02-28 ################################################################
#
import os
import sys
import math
import datetime
from optparse import OptionParser
from seiscomp3 import IO, DataModel, Core

'''
Station Class
	This internally loads a sc3 inv and exports the station file
	needed by hypoDD, it uses Event class to select stations for
	export, filter your events by this class before export.
'''
class Stations(object):
	def __init__(self, filename):
		self.inventory = None
		self.selection = { }

		ar = IO.XMLArchive()

		err = ar.open(filename)

		if err == False:
			print >>sys.stderr, "Filename '%s' is not accessible." % (filename)
			return

		obj = ar.readObject()
		ar.close()

		self.inventory = DataModel.Inventory.Cast(obj)

		self.selection = { }

	def select(self, n, s, l , c, t):
		err = True

		if type(self.inventory) == type(None): return err

		for i in range(0, self.inventory.networkCount()):
			net = self.inventory.network(i)
			if net.code() != n: 
				continue

			for j in range(0, net.stationCount()):
				sta = net.station(j)
				if sta.code() != s:
					continue

				for k in range(0, sta.sensorLocationCount()):
					loc = sta.sensorLocation(k)
					if loc.code() != l:
						continue

					for l in range(0, loc.streamCount()):
						cha = loc.stream(l)
						if cha.code()[0:2] != c[0:2]:
							continue

						s = sc3timeparse(cha.start())
						try:
							e = cha.end()
							e = sc3timeparse(e)
						except Core.ValueException:
							e = None

						if s > t: continue
						if e and e < t: continue

						## FINISH SELECTION
						ns = "%s%s" % (net.code(), sta.code())

						if ns not in self.selection:
							self.selection[ns] = ( ns, sta.latitude(), sta.longitude(), sta.elevation(), cha.depth() )

						err = False
						return err

		print >>sys.stderr," Warning, station (%s.%s.%s.%s @ %s) not resolved." % (n,s,l,c,t)
		return err

	def selectbye(self, e):
		if not isinstance(e, Event):
			raise Exception("Object has bad value")

		err = False

		if type(self.inventory) == type(None): return True

		for (nslc, time, phase, weight) in e.getpicks():
			(n, s, l, c) = nslc.split(".")
			errr = self.select(n,s,l,c,time)
			if errr: err = True

		return err

	def write(self, openfile):
		for k in self.selection:
			(ns, lat, lon, ele, dep) = self.selection[k]
			print >>openfile, "%-7s %8.3f %8.3f" % (ns, lat, lon)

'''
Event Class
	This handles one event, it is instantiated by 
	the method datafromxml and returned on success.
'''
class Event(object):
	def __init__(self, time, longitude, latitude, depth, magnitude, eh, ez, rms):
		self.time = time 

		try:
			self.longitude = float(longitude)
		except TypeError,e:
			print e
			raise Exception(" Bad longitude !")

		try:
			self.latitude = float(latitude)
		except TypeError,e:
			print e
			raise Exception(" Bad latitude !")

		try:
			self.depth = float(depth)
		except TypeError,e:
			print e
			raise Exception(" Bad depth !")

		try:
			self.magnitude = float(magnitude)
		except TypeError,e:
			self.magnitude = 0.0
			pass

		try:
			self.eh = eh
		except TypeError,e:
			self.eh = 0.0
			pass

		try:
			self.ez = ez
		except TypeError,e:
			self.ez = 0.0
			pass

		try:
			self.rms = rms
		except TypeError,e:
			self.rms = 0.0
			pass

		self.picks = { 'P': { }, 'S': { } }

	def addPick(self, network, station, location, channel, time, phase, weight):
		#
		## Check phase
		if phase not in self.picks.keys():
			return True

		#
		## Check that weight is 0.0
		if weight == 0.0:
			print >>sys.stderr," Warning, arrival with weight 0.0 on event %s stream (%s.%s.%s.%s)" % (self.time, network,station,location,channel)

		#
		## Check that weight is >1.0
		if weight > 1.0:
			print >>sys.stderr," Warning, arrival with weight >1.0 on event %s stream (%s.%s.%s.%s) -- normilized 1.0" % (self.time, network,station,location,channel)
			weight = 1.0

		#
		## Save pick
		nslc = "%s.%s.%s.%s" % (network, station, location, channel)
		if nslc in self.picks[phase]:
			print >>sys.stderr," Phase %s is already set for %s" % (phase, nslc)
			return True
		self.picks[phase][nslc] = (nslc, time, phase, weight)

		#
		## Done
		return False

	def getpicks(self, phase = None, nslc = None ):
		picks = [ ]

		for p in self.picks:
			if phase is not None and phase != p: continue

			if nslc is None:
				picks.extend(self.picks[p].values())
			elif nslc in self.picks[p]:
				picks.append(self.picks[p][nslc])

		return picks

	def write(self, openfile, evid):
		#
		## Output Event line
		print >>openfile,"# %04d %02d %02d %02d %02d %.4f %.4f %.4f %.2f %.2f %.1f %.1f %.2f %9d" % (self.time.year, self.time.month, self.time.day,
																									self.time.hour, self.time.minute, (float(self.time.second) + float(self.time.microsecond) / 1E6),
																									self.latitude, self.longitude, self.depth,
																									self.magnitude,
																									self.eh, self.ez, self.rms, evid)

		#
		## P-wave picks
		for (nslc, time, phase, weight) in self.getpicks():
			tt = time - self.time
			(n, s, l, c) = nslc.split(".")
			print >>openfile,"%-7s %8.4f %3.1f %1s" % ("%s%s" % (n,s), tt.total_seconds(), weight, phase)

		return

'''
Sc3 Time
'''
def sc3timeparse(sc3t):
	#
	## Get Core Time from TimeQuantity
	if isinstance(sc3t, DataModel.TimeQuantity):
		sc3t = sc3t.value()
	
	#
	## Send to standard datetime
	dt = datetime.datetime.utcfromtimestamp( float(sc3t.seconds()) + float(sc3t.microseconds()) / 1E6 )

	return dt

'''
Data Reader
'''
def datafromxml(filename):
	ev = None

	ar = IO.XMLArchive()

	err = ar.open(filename)
	if err == False:
		print >>sys.stderr, "Filename '%s' is not accessible." % (filename)
		return None

	obj = ar.readObject()
	ar.close()

	ep = DataModel.EventParameters.Cast(obj)

	if type(ep) == type(None):
		print >>sys.stderr,"File (%s) is no event, skipping." % filename
		return None

	if ep.eventCount == 0:
		print >>sys.stderr,"File (%s) has no events, skipping." % filename
		return None

	evt = ep.event(0)
	evt = DataModel.Event.Cast(evt)

	if type(evt) == type(None):
		print >>sys.stderr,"Cannot get event from file (%s), skipping." % filename
		return None

	if evt.preferredOriginID() == "":
		print >>sys.stderr,"No origin (%s), skipping." % filename
		return None

	print >>sys.stderr,"\nProcessing event %s (%s)" % (evt.publicID(), filename)

	if evt.preferredMagnitudeID() == "":
		print >>sys.stderr," No magnitude (%s)" % filename

	ori = ep.findOrigin(evt.preferredOriginID())
	mag = ori.findMagnitude(evt.preferredMagnitudeID())

	mag = mag.magnitude().value() if type(mag) != type(None) else None

	#
	## Assembly errors from Sc3 solution
	try:
		eh  = math.sqrt(math.pow(ori.latitude().uncertainty(), 2)  + math.pow(ori.longitude().uncertainty(), 2))
	except Core.ValueException:
		eh = 0.0
	
	try:
		ez  = ori.depth().uncertainty()
	except Core.ValueException:
		ez = 0.0

	try:
		rms = ori.quality().standardError()
	except Core.ValueException:
		rms = 0.0

	try:
		ev = Event(time = sc3timeparse(ori.time()),
				   longitude = ori.longitude().value(),
				   latitude = ori.latitude().value(),
				   depth = ori.depth().value(),
				   magnitude = mag,
				   eh = eh, ez = ez, rms = rms)
	except Exception,e:
		print >>sys.stderr," %s" % (str(e))
		return None

	for i in range(0,ori.arrivalCount()):
		#
		## Get Arrival
		arrival = ori.arrival(i)

		#
		## Get Pick
		pick = ep.findPick(arrival.pickID())
		if type(pick) == type(None):
			print >>sys.stderr," Invalid pick -- %s " % arrival.pickID()

		#
		## Get WaveformID
		waveform = pick.waveformID()

		#
		## Phase Hint
		phaseHint = pick.phaseHint()

		#
		## Load Pick into Event
		err = ev.addPick(waveform.networkCode(),
						waveform.stationCode(),
						waveform.locationCode(),
						waveform.channelCode(),
						sc3timeparse(pick.time()),
						phaseHint.code(),
						arrival.weight()
			)

		if err:
			print >>sys.stderr," Pick %s, %s, was rejected" % (phaseHint.code(), arrival.pickID())

	return ev

def make_cmdline_parser():
	# Create the parser
	#
	parser = OptionParser(usage="%prog [options] <files>", version="1.0", add_help_option = True)

	parser.add_option("--events", dest="eventfile", help="Filename to write events information and picks in hypoDD format", default=None)
	parser.add_option("--stations", dest="stationfile", help="Filename to write station information in hypoDD format", default=None)
	parser.add_option("--inventory", dest="inventory", help="Filename to read sc3 inventory from", default="inventory.xml")

	return parser

if __name__ == "__main__":
	parser = make_cmdline_parser()
	(options, args) = parser.parse_args()

	if options.eventfile is None and options.stationfile is None:
		print >>sys.stderr,"Nothing to do, please specify at least one of the output files."
		sys.exit(1)

	station = Stations(options.inventory)

	eventfile = None
	stationfile = None

	try:
		if options.eventfile:
			eventfile = open(options.eventfile, "w")
	except IOError,e:
		print >>sys.stderr,"Cannot open event file '%s'\n %s" % (options.eventfile, str(e))
		sys.exit(1)

	try:
		if options.stationfile:
			stationfile = open(options.stationfile, "w")
	except IOError,e:
		print >>sys.stderr,"Cannot open station file '%s'\n %s" % (options.stationfile, str(e))
		sys.exit(1)

	#
	## Parse all files
	sequenceid = 1
	for f in args:
		#
		## Parse data
		ev = datafromxml(f)

		#
		## Event is invalid, skip
		if ev is None: continue

		#
		## Filter the station class
		err = station.selectbye(ev)
		if err:
			print >>sys.stderr, " Warning. Station is not selected."

		#
		## Write to output
		if eventfile:
			ev.write(eventfile, sequenceid)

		#
		## Prepare a new sequence
		sequenceid += 1

	#
	## Close Event File if open
	if eventfile:
		eventfile.close()

	#
	## Output stations
	if stationfile:
		station.write(stationfile)
		stationfile.close()

	#
	## Make sure empty files are not left around
	if options.stationfile and os.path.getsize(options.stationfile) == 0:
		print >>sys.stderr,"Warning, removing empty station file '%s'" % options.stationfile
		os.unlink(options.stationfile)

	if options.eventfile and os.path.getsize(options.eventfile) == 0:
		print >>sys.stderr,"Warning, removing empty event file '%s'" % options.eventfile
		os.unlink(options.eventfile)

	#
	## Done
	sys.exit(0)
