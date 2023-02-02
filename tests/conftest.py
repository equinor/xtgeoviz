import os
import pathlib

import pytest


@pytest.fixture(name="testdir")
def fixure_testdir():
    """Relative path to xtgeo-testdata, defaulted to ../xtgeo-testdata."""
    relative_path_default = "../xtgeo-testdata"

    return pathlib.Path(os.environ.get("XTGEO_TESTDIR", relative_path_default))
