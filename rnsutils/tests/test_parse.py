import unittest

from rnsutils.instrument import RenoiseInstrument


class TestParse(unittest.TestCase):
    def test_open_template(self):
        # creates an empty instrument, which trigger template loading
        RenoiseInstrument()

    def test_missing_template(self):
        with self.assertRaises(Exception):
            RenoiseInstrument(template_filename='I dont exist.xnri')
