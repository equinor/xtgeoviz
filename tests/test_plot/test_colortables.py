import pathlib

import xtgeoviz.plot._colortables as ct

TPATH = pathlib.Path("../xtgeo-testdata")


def test_readfromfile():
    """Read color table from RMS file."""
    cfile = TPATH / "etc/colortables/colfacies.txt"
    ctable = ct.colorsfromfile(cfile)
    assert ctable[5] == (0.49019608, 0.38431373, 0.05882353)


def test_xtgeo_colors():
    """Read the XTGeo color table."""
    ctable = ct.xtgeocolors()
    assert ctable[5] == (0.000, 1.000, 1.000)
