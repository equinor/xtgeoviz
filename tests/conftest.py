import os
import pathlib

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--testdatapath",
        help="path to xtgeo-testdata, defaults to ../xtgeo-testdata"
        "and is overriden by the XTG_TESTPATH environment variable."
        "Experimental feature, not all tests obey this option.",
        action="store",
        default="../xtgeo-testdata",
    )
    parser.addoption(
        "--generate-plots",
        help="whether to generate plot files. The files are written to the"
        "pytest tmpfolder. In order to inspect whether plots are correctly"
        "generated, the files must be manually inspected.",
        action="store_true",
        default=False,
    )


@pytest.fixture(name="generate_plot")
def fixture_generate_plot(request):
    if "ROXENV" in os.environ:
        pytest.skip("Skip plotting tests in roxar environment")
    return request.config.getoption("--generate-plots")


@pytest.fixture(name="show_plot")
def fixture_xtgshow():
    """For eventual plotting, to be uses in an if sence inside a test."""
    if "ROXENV" in os.environ:
        pytest.skip("Skip plotting tests in roxar environment")
    if any(word in os.environ for word in ["XTGSHOW", "XTG_SHOW"]):
        return True
    return False


@pytest.fixture(name="testdir")
def fixure_testdir():
    """Relative path to xtgeo-testdata, defaulted to ../xtgeo-testdata."""
    relative_path_default = "../xtgeo-testdata"

    return pathlib.Path(os.environ.get("XTGEO_TESTDIR", relative_path_default))
