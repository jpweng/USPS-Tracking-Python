#!/usr/bin/env python3
# USPS API Tracking
# Tested on Python 3.4.2 running on Debian 8.7
# https://github.com/LiterallyLarry/USPS-Tracking-Python
#
# You must provide your API key in config.json as 'api_key' before running this program! You can sign up for an API key here: https://www.usps.com/business/web-tools-apis/welcome.htm

from urllib import request, parse
from sys import argv
from xml.etree import ElementTree
import argparse, json, sys, os

USPS_API_URL = "http://production.shippingapis.com/ShippingAPI.dll?API=TrackV2"

path = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(path, "config.json")) as config_file:
    config = json.load(config_file)
    api_key = config.get("api_key")

if not api_key:
    sys.exit("Error: Could not find USPS API key in config.json!")

parser = argparse.ArgumentParser(description='Tracks USPS numbers via Python.')

parser.add_argument('tracking_numbers', metavar='TRACKING_NUMBER', type=str, nargs='*',
                    help='a tracking number')
parser.add_argument('-s', action='store_true', default=False,
                    dest='show_tracking_number',
                    help='Show tracking number in output')
parser.add_argument('-n', action='store_false', default=True,
                    dest='show_tracking_extended',
                    help='Hide extended tracking information')
parser.add_argument('-m', action='store_true', default=False,
                    dest='show_minimal',
                    help='Repress UI')

def usps_track(numbers_list):
    xml = "<TrackRequest USERID=\"%s\">" % api_key
    for track_id in numbers_list:
        xml += "<TrackID ID=\"%s\"></TrackID>" % track_id
    xml += "</TrackRequest>"
    target = "%s&%s" % (USPS_API_URL, parse.urlencode({ "XML" : xml }))
    request_obj = request.urlopen(target)
    result = request_obj.read()
    request_obj.close()
    return result

class TrackingContext:
    def pattern (self):
        with open(os.path.join(path, "config.json")) as config_file:
            config = json.load(config_file)
            tracking_number_pattern = config.get("tracking_number_pattern")

            if not tracking_number_pattern:
                sys.exit("Error: Could not find tracking_number_pattern in config.json!")

            return tracking_number_pattern
        sys.exit("Error: Failed to open config.json!")

    def process (self, trackingNumer):
        track_xml = usps_track([trackingNumer])
        track_result = ElementTree.ElementTree(ElementTree.fromstring(track_xml))
        for result in track_result.findall('Description'):
            print(result.text)
        for number, result in enumerate(track_result.findall('.//TrackInfo')):
            summary = result.find('TrackSummary')
            if summary is None:
                print('Error in XML!')
                print(track_xml)
            else:
                print('%s' % summary.text)
                #if args.show_tracking_extended:
                details = result.findall('TrackDetail')
                for number_2, detailed_result in enumerate(details):
                    if number_2+1 == len(details):
                        print('  └ %s' % detailed_result.text)
                    else:
                        print('  ├ %s' % detailed_result.text)

class TrackingRequestsGeneration:
    def __init__ (self, trackingContext = TrackingContext ()):
        self.trackingContext = trackingContext

    def preAndSuffixTuple (self):
        tracking_number_pattern = self.trackingContext.pattern ()
        prefix = tracking_number_pattern[:tracking_number_pattern.find ('.')]
        suffix = tracking_number_pattern[tracking_number_pattern.rfind ('.') + 1:]
        return prefix, suffix

    def requestAll (self):
        prefix, suffix = self.preAndSuffixTuple ()
        count = self.trackingContext.pattern ().count ('.')
        for i in range (10 ** count):
            trackingNumber = prefix + '0' * (count - len (str (i))) + str (i) + suffix
            self.trackingContext.process (trackingNumber)
    
if __name__ == "__main__":
    TrackingRequestsGeneration ().requestAll ()