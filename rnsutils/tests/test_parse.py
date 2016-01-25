from rnsutils.instrument import RenoiseInstrument


def test_open_template():
    # creates an empty instrument, which trigger template loading
    RenoiseInstrument()
