#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
################################################################################
#																			  #
#   SeisComp3 XML to hypoDD converter										  #
#   Copyright (C) 2015  Marcelo Belentani de Bianchi						   #
#																			  #
#   This program is free software; you can redistribute it and/or modify	   #
#   it under the terms of the GNU General Public License as published by	   #
#   the Free Software Foundation; either version 2 of the License, or		  #
#   (at your option) any later version.										#
#																			  #
#   This program is distributed in the hope that it will be useful,			#
#   but WITHOUT ANY WARRANTY; without even the implied warranty of			 #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the			  #
#   GNU General Public License for more details.							   #
#																			  #
#   You should have received a copy of the GNU General Public License along	#
#   with this program; if not, write to the Free Software Foundation, Inc.,	#
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.				#
#																			  #
#### 2015-02-28 ################################################################
#
import sys, math
from seiscomp3 import IO, DataModel
import datetime

'''
Station Class
	This internally loads a sc3 inv and exports the station file
	needed by hypoDD, it uses Event class to select stations for
	export, filter your events by this class before export.
'''
class Stations(object):
	def __init__(self, inventory):
		pass

	def selectbyevent(self, event):
		pass

	def write(self, openfile):
		pass

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

		self.picks = { }

		self.picks["P"] = []
		self.picks["S"] = []

	def addPick(self, network, station, location, channel, time, phase, weight):
		#
		## Check phase
		if phase not in self.picks.keys():
			return False

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
		self.picks[phase].append(("%s.%s.%s.%s" % (network,station,location,channel), time, phase, weight))

		#
		## Done
		return True

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
		for (nslc, time, phase, weight) in self.picks['P']:
			tt = time - self.time
			(n, s, l, c) = nslc.split(".")
			print >>openfile,"%-7s %8.4f %3.1f %1s" % ("%s%s" % (n,s), tt.total_seconds(), weight, phase)

		#
		## S-wave picks
		for (nslc, time, phase, weight) in self.picks['S']:
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
	ar.open(filename)
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

	if evt.preferredMagnitudeID() == "":
		print >>sys.stderr,"No magnitude (%s)" % filename

	print >>sys.stderr,"\nProcessing event %s (%s)" % (evt.publicID(), filename)

	ori = ep.findOrigin(evt.preferredOriginID())
	mag = ori.findMagnitude(evt.preferredMagnitudeID())

	mag = mag.magnitude().value() if type(mag) != type(None) else None

	#
	## Assembly errors from Sc3 solution
	eh  = math.sqrt(math.pow(ori.latitude().uncertainty(), 2)  + math.pow(ori.longitude().uncertainty(), 2))
	ez  = ori.depth().uncertainty()
	rms = ori.quality().standardError()

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

	for i in range(ori.arrivalCount()):
		#
		## Get Arrival
		arrival = ori.arrival(i)

		#
		## Get Pick
		pick = ep.findPick(arrival.pickID())
		if type(pick) == type(None):
			print >>sys.stderr," Invalid pick -- " % arrival.pickID()

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

		if not err:
			print >>sys.stderr," Pick %s, %s, was rejected" % (phaseHint.code(), arrival.pickID())

	return ev

if __name__ == "__main__":
	events = [ ]

	station = Stations(None)

	#
	## Parse all files
	for f in sys.argv:
		#
		## Parse data
		ev = datafromxml(f)

		#
		## Event is invalid, skip
		if ev is None: continue

		#
		## Filter the station class
		station.selectbyevent(ev)

		#
		## Save the event
		events.append(ev)

	#
	## Output events
	id = 1
	for ev in events:
		ev.write(sys.stdout, id)
		id += 1

	#
	## Output stations
	station.write(sys.stdout)

	#
	## Done
	sys.exit(0)
