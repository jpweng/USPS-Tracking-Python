#!/usr/bin/env python3
# USPS API Tracking
# Tested on Python 3.4.2 running on Debian 8.7
# https://github.com/LiterallyLarry/USPS-Tracking-Python
#
# You must provide your API key in config.json as 'api_key' before running this program! You can sign up for an API key here: https://www.usps.com/business/web-tools-apis/welcome.htm

from urllib import request, parse
from sys import argv
from xml.etree import ElementTree
import sqlite3
from sqlite3 import Error
import argparse, json, sys, os
import threading, queue, time

USPS_API_URL = "http://production.shippingapis.com/ShippingAPI.dll?API=TrackV2"

path = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(path, "config.json")) as config_file:
    config = json.load(config_file)
    api_key = config.get("api_key")

if not api_key:
    sys.exit("Error: Could not find USPS API key in config.json!")

q = queue.Queue ()

class TrackingProcessing:
    def __init__ (self, dataCondition = lambda data : True):
        self.createDb ()
        self.dataCondition = dataCondition

    def createDb (self):
        with open (os.path.join(path, "config.json")) as config_file:
            config = json.load(config_file)
            dbFolder = config.get("db_folder")
            if not os.path.isdir (dbFolder):
                os.mkdir (dbFolder)
            self.filename = os.path.join (dbFolder, "USPSTracking.db")
            self.connection = None
            try:
                self.connection = sqlite3.connect (self.filename)
                self.createTable ()
            except Error as e:
                print (e)

    def createTable (self):
        try:
            sql_create_table = """ CREATE TABLE IF NOT EXISTS trackings (
                               trackingNumber text NOT NULL PRIMARY KEY,
                               summary text NOT NULL,
                               details text NOT NULL
                            ); """
            c = self.connection.cursor()
            c.execute (sql_create_table)
        except Error as e:
            print (e)

    def process (self, trackingData): # list of tuples (trackingNumber, summary, details):
        cur = self.connection.cursor ()
        cur.execute ('BEGIN TRANSACTION')
        for data in trackingData:
            if self.dataCondition (data):
                #print (data[2], '\r\n')
                cur.execute (' INSERT OR IGNORE INTO trackings (trackingNumber, summary, details) VALUES (?, ?, ?)', data)
        cur.execute ('COMMIT')

    def consume (self):
        global q
        while True:
            if not q.empty ():
                trackingData = q.get ()
                if trackingData == 'stop':
                    return
                self.process (trackingData)

    def __del__ (self):
        if self.connection:
            self.connection.close ()

class TrackingContext:
    def __init__ (self, chunkSize = 100):
        assert 0 < chunkSize < 1000
        self.trackingChunk = []
        self.chunkSize = chunkSize

    def usps_track (self, numbers_list):
        xml = "<TrackRequest USERID=\"%s\">" % api_key
        for track_id in numbers_list:
            xml += "<TrackID ID=\"%s\"></TrackID>" % track_id
        xml += "</TrackRequest>"
        target = "%s&%s" % (USPS_API_URL, parse.urlencode({ "XML" : xml }))
        request_obj = request.urlopen(target)
        result = request_obj.read()
        request_obj.close()
        return result

    def pattern (self):
        with open(os.path.join(path, "config.json")) as config_file:
            config = json.load(config_file)
            tracking_number_pattern = config.get("tracking_number_pattern")

            if not tracking_number_pattern:
                sys.exit("Error: Could not find tracking_number_pattern in config.json!")

            return tracking_number_pattern
        sys.exit("Error: Failed to open config.json!")

    def process (self, trackingNumer):
        if len (self.trackingChunk) < self.chunkSize:
            self.trackingChunk.append (trackingNumer)
        if len (self.trackingChunk) == self.chunkSize:
            self.processChunk ()
            self.trackingChunk = []

    def notifyEnd (self):
        self.processChunk ()

    def addTrackingDataToQueue (self, trackingData):
        global q
        q.put (trackingData)

    def processChunk (self):
        if self.trackingChunk == []:
            return

        track_xml = self.usps_track(self.trackingChunk)
        track_result = ElementTree.ElementTree(ElementTree.fromstring(track_xml))

        trackingData = []

        for number, result in enumerate(track_result.findall('.//TrackInfo')):
            summary = result.find('TrackSummary')
            if summary is None:
                continue

            details = result.findall ('TrackDetail')
            detailTexts = ""
            for number_2, detailed_result in enumerate(details):
                detailTexts += detailed_result.text + "\r\n"
            data = (str (self.trackingChunk[number]), summary.text, detailTexts)
            trackingData.append (data)

        self.addTrackingDataToQueue (trackingData)

class CountThreads:
    def nThreads (self):
        with open(os.path.join(path, "config.json")) as config_file:
            config = json.load(config_file)
            return config.get("numThreads")

class TrackingRequestsGeneration:
    def __init__ (self, trackingContextMap = lambda: TrackingContext (), countThreads = CountThreads (), dataCondition = lambda data : True):
        self.nThreads = countThreads.nThreads ()
        self.trackingContext = [trackingContextMap () for i in range (self.nThreads)]
        self.dataCondition = dataCondition

    def preAndSuffixTuple (self):
        tracking_number_pattern = self.trackingContext[0].pattern ()
        prefix = tracking_number_pattern[:tracking_number_pattern.find ('.')]
        suffix = tracking_number_pattern[tracking_number_pattern.rfind ('.') + 1:]
        return prefix, suffix

    def processRange (self, myRange, prefix, suffix, count, threadIndex):
        for i in myRange:
            trackingNumber = prefix + '0' * (count - len (str (i))) + str (i) + suffix
            self.trackingContext[threadIndex].process (trackingNumber)
        self.trackingContext[threadIndex].notifyEnd ()

    def consume (self):
        trackingProcessing = TrackingProcessing (self.dataCondition)
        trackingProcessing.consume ()

    def requestAll (self):
        startTime = time.time ()

        prefix, suffix = self.preAndSuffixTuple ()
        count = self.trackingContext[0].pattern ().count ('.')

        nElems = 10 ** count
        rootRange = range (nElems)
        partiLen = int (nElems / self.nThreads)
        partitions = [rootRange[i : i + partiLen] for i in range (0, nElems, partiLen)]
        
        threads = [
            threading.Thread (target = self.processRange, args = (partitions[i], prefix, suffix, count, i))
            for i in range (self.nThreads)
            ]

        consumerThread = threading.Thread (target = self.consume)

        consumerThread.start ()

        for thread in threads:
            thread.start ()

        for thread in threads:
            thread.join ()

        global q
        q.put ('stop')

        consumerThread.join ()

        endTime = time.time ()
        print ("Elapsed time: ", endTime - startTime)
    
if __name__ == "__main__":
    TrackingRequestsGeneration (dataCondition = lambda data : 'PHILADELPHIA' in data[2]).requestAll ()