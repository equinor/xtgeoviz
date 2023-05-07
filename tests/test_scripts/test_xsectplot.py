"""Module for testing stand-alone scripts and/or entrypoints functions."""
import pytest
import xtgeo

from xtgeoviz import xsectplot
from xtgeoviz.frontends._xsectplotting_config import config_defaults, data_merge
from xtgeoviz.frontends.xsectplotting import _Xsections, _XsectSettings

# testdata (xtgeo-testdata), relative to testdir
WELLSET1 = "wells/drogon/1"
SURFACESET1 = "surfaces/drogon/1"
OUTLINE = "polygons/reek/1/closedpoly1.pol"
CUBE = "cubes/drogon/ampl_local_a4.segy"


def test_xsectplotting_config_defaults():
    """Test _xsectplottings_config() config_defaults method."""

    yamlresult = config_defaults()
    assert isinstance(yamlresult, str)

    dictresult = config_defaults(as_yaml=False)
    assert isinstance(dictresult, dict)
    assert dictresult["input"]["wells"]["zonelog"] == "ZONELOG"


def test_xsectplotting_config_dict_merge_ok():
    """Test _xsectplottings_config() data_merge method."""

    userinput = {
        "input": {
            "wells": {"zonelog": "MYZONELOG"},
        }
    }

    dictresult = config_defaults(as_yaml=False)
    update = data_merge(dictresult, userinput)
    assert update["input"]["wells"]["zonelog"] != "ZONELOG"
    assert update["input"]["wells"]["zonelog"] == "MYZONELOG"
    assert update["plotsettings"]["surfaces"]["contacts"]["colors"] == "rainbow"


def test_xsectplotting_config_dict_merge_shall_fail():
    """Test _xsectplottings_config() data_merge method shall fail due to invalid."""

    userinput = {
        "input": {
            "invalid_word": {"zonelog": "MYZONELOG"},
        }
    }

    dictresult = config_defaults(as_yaml=False)
    with pytest.raises(ValueError, match="Input contains invalid fields: invalid_word"):
        _ = data_merge(dictresult, userinput)


def test_xsects_settings_class():
    """Test the internal XsectsSettings dataclass class."""

    xsec = _XsectSettings()

    assert xsec.design_dpi == 100
    assert xsec.wells_zonelog_zoneshift == 0


def test_xsects_input_load_wells(testdir):
    """Test loading wells for xsect."""
    inputs = {
        "wells": {
            "folder": str(testdir / WELLSET1),
            "wildcard": "55*",
            "zonelog": "Zone",
        }
    }

    xapp = _Xsections(inputdata=inputs)
    xapp.load_wells()
    wellnames = [well.name for well in xapp.wells["wlist"]]
    for wname in ["55_33-1", "55_33-2", "55_33-3", "55_33-A-1", "55_33-A-2"]:
        assert wname in wellnames


def test_xsects_input_load_surfaces(testdir):
    """Test loading wells for xsect."""
    inputs = {
        "surfaces": {
            "primary": {
                "folder": str(testdir / SURFACESET1),
                "wildcard": "*",
                "names": ["TopVolantis", "TopTherys", "TopVolon", "BaseVolantis"],
            },
        },
    }

    xapp = _Xsections(inputdata=inputs)
    xapp.load_surfaces()
    surfnames = [surf.name for surf in xapp.surfaces["primary"]]
    for sname in ["TopTherys", "BaseVolantis"]:
        assert sname in surfnames


def test_xsectplot_function(testdir, tmp_path):
    """Make plots using python input."""

    inputs = {
        "wells": {
            "folder": str(testdir / WELLSET1),
            "wildcard": "55_33-A-4*",
            "zonelog": "Zone",
        },
        "surfaces": {
            "primary": {
                "folder": str(testdir / SURFACESET1),
                "wildcard": "*",
                "names": ["TopVolantis", "TopTherys", "TopVolon", "BaseVolantis"],
            },
        },
        "outline": str(testdir / OUTLINE),
    }
    psettings = {
        "design": {
            "zrange": [1550, 1750],
        },
    }

    outputs = {
        "plotfolder": str(tmp_path),
        "format": "png",
    }

    # call the top plotter routine
    xsectplot(inputdata=inputs, plotsettings=psettings, output=outputs)
    myplot = tmp_path / "55_33-A-4.png"
    assert myplot.is_file()


def test_xsectplot_function_input_objectlists(testdir, tmp_path):
    """Make plots using python input, where wells and surfaces are preloaded."""

    wells = ["55_33-A-1.rmswell", "55_33-A-4.rmswell"]
    surfaces = [
        "01_topvolantis.gri",
        "02_toptherys.gri",
        "03_topvolon.gri",
        "04_basevolantis.gri",
    ]

    wlist = []
    for well in wells:
        wlist.append(xtgeo.well_from_file(testdir / WELLSET1 / well))

    slist = []
    for surf in surfaces:
        slist.append(xtgeo.surface_from_file(testdir / SURFACESET1 / surf))

    inputs = {
        "wells": {
            "objects": wlist,
            "zonelog": "Zone",
        },
        "surfaces": {
            "primary": {
                "objects": slist,
                "names": ["TopVolantis", "TopTherys", "TopVolon", "BaseVolantis"],
            },
        },
    }
    psettings = {
        "design": {
            "zrange": [1550, 1750],
        },
        "wells": {
            "zonelog": {
                "zoneshift": 0,
            }
        },
    }

    outputs = {
        "plotfolder": str(tmp_path),
        "format": "png",
    }

    # call the top plotter routine
    xsectplot(inputdata=inputs, plotsettings=psettings, output=outputs)
    myplot = tmp_path / "55_33-A-4.png"
    assert myplot.is_file()


def test_xsectplot_function_include_cube(testdir, tmp_path):
    """Make plots using python input, where wells and surfaces are preloaded."""

    wells = ["55_33-A-4.rmswell"]
    surfaces = [
        "01_topvolantis.gri",
        "02_toptherys.gri",
        "03_topvolon.gri",
        "04_basevolantis.gri",
    ]

    wlist = []
    for well in wells:
        wlist.append(xtgeo.well_from_file(testdir / WELLSET1 / well))

    slist = []
    for surf in surfaces:
        slist.append(xtgeo.surface_from_file(testdir / SURFACESET1 / surf))

    cube = xtgeo.cube_from_file(testdir / CUBE)

    inputs = {
        "wells": {
            "objects": wlist,
            "zonelog": "Zone",
        },
        "surfaces": {
            "primary": {
                "objects": slist,
                "names": ["TopVolantis", "TopTherys", "TopVolon", "BaseVolantis"],
            },
        },
        "cube": cube,
    }
    psettings = {
        "design": {
            "zrange": {
                "default": [1000, 2000],
                "55_33.*": [1450, 1750],  # use a python regex for multiple wells
            },
        },
        "wells": {
            "zonelog": {
                "zoneshift": 0,
            }
        },
        "surfaces": {
            "primary": {
                "fill": False,
            },
        },
        "cube": {
            "range": [-0.33, 0.33],
            "sampling": "trilinear",
        },
    }

    outputs = {
        "plotfolder": str(tmp_path),
        "format": "png",
    }

    # call the top plotter routine
    xsectplot(inputdata=inputs, plotsettings=psettings, output=outputs)
    myplot = tmp_path / "55_33-A-4.png"
    assert myplot.is_file()
