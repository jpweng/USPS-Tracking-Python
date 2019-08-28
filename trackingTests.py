import unittest
from tracking import TrackingContext, TrackingRequestsGeneration, TrackingProcessing
import sqlite3
from sqlite3 import Error

class FakeTrackingContext (TrackingContext):
    def __init__ (self, generated):
        self.generated = generated

    def pattern (self):
        return "EW00525141.US"

    def process (self, trackingNumer):
        self.generated.append (trackingNumer)

    def notifyEnd (self):
        pass

class TestsTrackingRange (unittest.TestCase):
    def setUp(self):
        self.generated = []
        self.trackingRange = TrackingRequestsGeneration (FakeTrackingContext (self.generated))
        
    def testPrefix (self):
        self.assertEqual ("EW00525141", self.trackingRange.preAndSuffixTuple ()[0])
    def testSuffix (self):
        self.assertEqual ("US", self.trackingRange.preAndSuffixTuple ()[1])
    def testGenerated (self):
        self.trackingRange.requestAll ()
        self.assertListEqual (
            self.generated,
            ["EW005251410US", "EW005251411US", "EW005251412US", "EW005251413US", "EW005251414US",
            "EW005251415US", "EW005251416US", "EW005251417US", "EW005251418US", "EW005251419US"])

class RamDbProcessing (TrackingProcessing):
    def createDb (self):
        self.connection = None
        try:
            self.connection = sqlite3.connect (":memory:")
            self.createTable ()
        except Error as e:
            print (e)

class TestsSqlite (unittest.TestCase):
    def setUp (self):
        self.processing = RamDbProcessing ()
        self.trackingData = [
            ("EW005251411US",
            "Your item was delivered in FRANCE at 11:28 am on August 27, 2019.",
            "Held at Delivery Depot/Delivery Office, 08/23/2019, 12:33 pm, FRANCE \
                Addressee not available - Will attempt delivery on next working day, August 20, 2019, 10:24 am, FRANCE \
                Out for Delivery, August 20, 2019, 6:51 am, FRANCE \
                Arrived at USPS Regional Facility, August 18, 2019, 2:59 am, JAMAICA NY INTERNATIONAL DISTRIBUTION CENTER\
                USPS in possession of item, August 17, 2019, 12:16 pm, PHILADELPHIA, PA 19130"),
            ("EW005251412US",
            "Your item was lost forever.",
            "Held at Delivery Depot/Delivery Office, 08/23/2019, 12:33 pm, UTOPIA \
                Addressee not available - Will attempt delivery on next working day, August 20, 2019, 10:24 am, FRANCE \
                Out for Delivery, August 20, 2019, 6:51 am, FRANCE \
                Arrived at USPS Regional Facility, August 18, 2019, 2:59 am, JAMAICA NY INTERNATIONAL DISTRIBUTION CENTER\
                USPS in possession of item, August 17, 2019, 12:16 pm, PHILADELPHIA, PA 19130"),
            ("EW005251413US",
            "Good luck dealing with USPS",
            "Held at Delivery Depot/Delivery Office, 08/23/2019, 12:33 pm, WORSTCOSTUMERSERVICEEVER \
                Addressee not available - Will attempt delivery on next working day, August 20, 2019, 10:24 am, FRANCE \
                Out for Delivery, August 20, 2019, 6:51 am, FRANCE \
                Arrived at USPS Regional Facility, August 18, 2019, 2:59 am, JAMAICA NY INTERNATIONAL DISTRIBUTION CENTER\
                USPS in possession of item, August 17, 2019, 12:16 pm, PHILADELPHIA, PA 19130"),
        ]

    def testInsert (self):
        self.processing.process (self.trackingData)
        cur = self.processing.connection.cursor ()
        cur.execute ("SELECT * FROM trackings")
        result = cur.fetchall ()
        
        self.assertEqual (len (result), 3)

    def testSelectTracking (self):
        self.processing.process (self.trackingData)
        cur = self.processing.connection.cursor ()
        cur.execute ("SELECT * FROM trackings WHERE trackingNumber = ?", ("EW005251411US",))
        result = cur.fetchall ()

        self.assertIn ("FRANCE", result[0][1])
        self.assertIn ("PHILADELPHIA", result[0][2])

    def testInsertDuplicateTrackingNumber (self):
        self.processing.process (self.trackingData)
        self.processing.process ([("EW005251411US", "This is a duplicate", "details")])
        cur = self.processing.connection.cursor ()
        cur.execute ("SELECT * FROM trackings WHERE trackingNumber = ?", ("EW005251411US",))
        result = cur.fetchall ()

        self.assertEqual (len (result), 1)
