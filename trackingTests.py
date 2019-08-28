import unittest
from tracking import TrackingContext
from tracking import TrackingRequestsGeneration

class FakeTrackingContext (TrackingContext):
    def __init__ (self, generated):
        self.generated = generated

    def pattern (self):
        return "EW00525141.US"

    def process (self, trackingNumer):
        self.generated.append (trackingNumer)

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
