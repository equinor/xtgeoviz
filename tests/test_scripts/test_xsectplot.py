"""Module for testing stand-alone scripts and/or entrypoints functions."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
import xtgeo

from xtgeoviz import xsectplot
from xtgeoviz.frontends import _xsectplotting_plotting as plotting_helpers
from xtgeoviz.frontends._xsectplotting_config import (
    ConfigError,
    config_complete,
    config_defaults,
    data_merge,
)
from xtgeoviz.frontends.xsectplotting import _Xsections, _XsectSettings

# testdata (xtgeo-testdata), relative to testdir
WELLSET1 = "wells/drogon/1"
SURFACESET1 = "surfaces/drogon/1"
OUTLINE = "polygons/reek/1/closedpoly1.pol"
CUBE = "cubes/drogon/ampl_local_a4.segy"


def _config_app(zrange, primary, wells=None, cube=None, grid=None, gridproperty=None):
    config = config_defaults(as_yaml=False)
    assert isinstance(config, dict)
    config["plotsettings"]["design"]["zrange"] = zrange
    return SimpleNamespace(
        config=config,
        surfaces={"primary": primary},
        wells={"wlist": wells or []},
        cube=cube,
        grid=grid,
        gridproperty=gridproperty,
    )


class TestXsectplottingConfig:
    """Tests for default config creation and recursive overrides."""

    def test_defaults(self):
        """Config defaults are available as YAML and a Python mapping."""
        yamlresult = config_defaults()
        assert isinstance(yamlresult, str)

        dictresult = config_defaults(as_yaml=False)
        assert isinstance(dictresult, dict)
        assert dictresult["input"]["wells"]["zonelog"] == "ZONELOG"

    def test_dict_merge_ok(self):
        """A valid nested override leaves unspecified defaults intact."""
        userinput = {
            "input": {
                "wells": {"zonelog": "MYZONELOG"},
            }
        }

        dictresult = config_defaults(as_yaml=False)
        update = data_merge(dictresult, userinput)
        assert update["input"]["wells"]["zonelog"] == "MYZONELOG"
        assert update["plotsettings"]["surfaces"]["contacts"]["colors"] == "rainbow"

    def test_dict_merge_rejects_invalid_top_level_key(self):
        """Unknown top-level input keys are rejected."""
        userinput = {
            "input": {
                "invalid_word": {"zonelog": "MYZONELOG"},
            }
        }

        dictresult = config_defaults(as_yaml=False)
        with pytest.raises(
            ValueError, match="Input contains invalid fields: invalid_word"
        ):
            data_merge(dictresult, userinput)

    def test_dict_merge_rejects_invalid_nested_key(self):
        """Unknown keys nested under a valid section are rejected."""
        userinput = {
            "input": {
                "wells": {"invalid_word": "MYZONELOG"},
            }
        }

        dictresult = config_defaults(as_yaml=False)
        with pytest.raises(
            ValueError, match="Input contains invalid fields: invalid_word"
        ):
            data_merge(dictresult, userinput)

    def test_dict_merge_appends_lists_and_replaces_scalars(self):
        """List values extend while scalar settings are overridden."""
        defaults = {"settings": {"values": [1, 2], "label": "default"}}
        userinput = {"settings": {"values": [3], "label": "custom"}}

        merged = data_merge(defaults, userinput)

        assert merged == {"settings": {"values": [1, 2, 3], "label": "custom"}}

    def test_dict_merge_appends_scalar_to_list(self):
        """A scalar override is appended when the existing value is a list."""
        defaults = {"settings": {"values": [1, 2]}}

        merged = data_merge(defaults, {"settings": {"values": 3}})

        assert merged == {"settings": {"values": [1, 2, 3]}}

    def test_dict_merge_rejects_non_dict_nested_value(self):
        """A mapping cannot be replaced with a scalar during recursive merging."""
        with pytest.raises(ConfigError, match="Cannot merge non-dict"):
            data_merge({"settings": {"value": 1}}, {"settings": "invalid"})

    def test_dict_merge_rejects_unsupported_superset(self):
        """Unsupported value types are rejected instead of silently discarded."""
        with pytest.raises(ConfigError, match="NOT IMPLEMENTED"):
            data_merge((1, 2), {})

    @pytest.mark.parametrize("superset", [None, "default", 10, 2.5])
    def test_dict_merge_replaces_scalar_superset(self, superset):
        """Null and scalar defaults are replaced by the supplied value."""
        subset = {"replacement": True}

        assert data_merge(superset, subset) is subset

    def test_settings_class_defaults(self):
        """The plot settings object starts with documented defaults."""
        settings = _XsectSettings()

        assert settings.design_dpi == 100
        assert settings.wells_zonelog_zoneshift == 0

    def test_config_complete_calculates_smart0_range(self):
        """Smart0 expands the first and last surface elevations by ten units."""
        primary = [
            SimpleNamespace(values=np.array([1234.0, 1300.0])),
            SimpleNamespace(values=np.array([1700.0, 1788.0])),
        ]
        app = _config_app("smart0", primary)

        config_complete(app)

        assert app.config["plotsettings"]["design"]["zrange"] == [1220, 1800]
        assert app.config["plotsettings"]["wells"]["zonelog"]["colordict"] == {
            value: value for value in range(100)
        }

    def test_config_complete_defaults_empty_range_to_smart0(self):
        """An empty configured range selects smart0."""
        primary = [
            SimpleNamespace(values=np.array([1234.0])),
            SimpleNamespace(values=np.array([1788.0])),
        ]
        app = _config_app("", primary)

        config_complete(app)

        assert app.config["plotsettings"]["design"]["zrange"] == [1220, 1800]

    def test_config_complete_caps_smart1_range_to_wells(self):
        """Smart1 caps the surface range at the highest well elevation."""
        primary = [
            SimpleNamespace(values=np.array([1234.0])),
            SimpleNamespace(values=np.array([1788.0])),
        ]
        wells = [
            SimpleNamespace(
                dataframe={
                    "Z_TVDSS": SimpleNamespace(values=np.array([1500.0, 1504.0]))
                },
            )
        ]
        app = _config_app("smart1", primary, wells=wells)

        config_complete(app)

        assert app.config["plotsettings"]["design"]["zrange"] == [1220, 1510]

    def test_config_complete_applies_per_well_regex_ranges(self):
        """User regex ranges override the global default for matching wells."""
        primary = []
        wells = [
            SimpleNamespace(name="55_33-1"),
            SimpleNamespace(name="other-well"),
        ]
        app = _config_app(
            {"default": [1000, 2000], "55_33.*": [1450, 1750]},
            primary,
            wells=wells,
        )

        config_complete(app)

        assert app.config["plotsettings"]["design"]["zrange"] == {
            "55_33-1": [1450, 1750],
            "other-well": [1000, 2000],
        }

    def test_config_complete_uses_cube_and_grid_ranges(self):
        """Unset cube and grid ranges are derived from their property values."""
        app = _config_app(
            [1000, 2000],
            [],
            cube=SimpleNamespace(values=np.array([-2.0, 5.0])),
            grid=SimpleNamespace(),
            gridproperty=SimpleNamespace(values=np.array([10.0, 40.0])),
        )

        config_complete(app)

        assert app.config["plotsettings"]["cube"]["range"] == [-2.0, 5.0]
        assert app.config["plotsettings"]["grid"]["range"] == [10.0, 40.0]

    def test_config_complete_rejects_unknown_zrange_mode(self):
        """Unsupported range values fail with an actionable error."""
        app = _config_app(object(), [])

        with pytest.raises(RuntimeError, match="Cannot process/understand the zrange"):
            config_complete(app)


class TestXsectInputLoading:
    """Tests for loading inputs into the cross-section app."""

    def test_load_wells_rejects_empty_folder(self, tmp_path):
        inputs = {
            "wells": {
                "folder": str(tmp_path),
                "wildcard": "*.rmswell",
            }
        }
        xapp = _Xsections(inputdata=inputs)

        with pytest.raises(SystemExit, match="Cannot plot, no wells as input"):
            xapp.load_wells()

    def test_load_preloaded_wells_and_optional_logs(self):
        wells = [object()]
        inputs = {
            "wells": {
                "objects": wells,
                "zonelog": "Zone",
                "facieslog": "Facies",
                "perflog": "Perf",
            }
        }
        xapp = _Xsections(inputdata=inputs)

        xapp.load_wells()

        assert xapp.wells["wlist"] is wells
        assert xapp.wells["facieslog"] == "Facies"
        assert xapp.wells["perflog"] == "Perf"

    def test_load_wells(self, testdir):
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

    def test_load_surfaces(self, testdir):
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

    def test_load_surfaces_uses_default_names(self, testdir):
        inputs = {
            "surfaces": {
                "primary": {
                    "folder": str(testdir / SURFACESET1),
                    "wildcard": "*.gri",
                },
            },
        }
        xapp = _Xsections(inputdata=inputs)

        xapp.load_surfaces()

        assert [surface.name for surface in xapp.surfaces["primary"]] == [
            "Surface_0",
            "Surface_1",
            "Surface_2",
            "Surface_3",
        ]

    def test_load_surfaces_rejects_non_xtgeo_objects(self):
        inputs = {"surfaces": {"primary": {"objects": [object()]}}}
        xapp = _Xsections(inputdata=inputs)

        with pytest.raises(RuntimeError, match="Surface object are not XTGeo objects"):
            xapp.load_surfaces()

    def test_load_outline_from_preloaded_object(self, testdir):
        outline = xtgeo.polygons_from_file(testdir / OUTLINE)
        xapp = _Xsections(inputdata={"outline": outline})

        xapp.load_outline()

        assert xapp.outline is outline

    def test_load_cube_from_path(self, testdir):
        xapp = _Xsections(inputdata={"cube": str(testdir / CUBE)})

        xapp.load_cube()

        assert isinstance(xapp.cube, xtgeo.Cube)

    def test_load_missing_cube_sets_none(self):
        xapp = _Xsections(inputdata={"wells": {}})

        xapp.load_cube()

        assert xapp.cube is None

    @pytest.mark.parametrize("fromgrid", [None, "geometry.roff"])
    def test_load_grid_property_and_optional_geometry(self, monkeypatch, fromgrid):
        inputs = {
            "surfaces": {"fromgrid": fromgrid},
            "grid": {
                "geometry": "geometry.roff",
                "property": {"file": "property.roff", "name": "PORO"},
            },
        }
        xapp = _Xsections(inputdata=inputs)
        grid = object()
        gridproperty = object()
        grid_reader = MagicMock(return_value=grid)
        property_reader = MagicMock(return_value=gridproperty)
        monkeypatch.setattr(xtgeo, "grid_from_file", grid_reader)
        monkeypatch.setattr(xtgeo, "gridproperty_from_file", property_reader)

        xapp.load_grid()

        if fromgrid is None:
            grid_reader.assert_called_once_with("geometry.roff")
            assert xapp.grid is grid
        else:
            grid_reader.assert_not_called()
            assert xapp.grid is None
        property_reader.assert_called_once_with(
            "property.roff", name="PORO", date=False
        )
        assert xapp.gridproperty is gridproperty

    def test_load_grid_without_complete_inputs_does_nothing(self, monkeypatch):
        xapp = _Xsections(inputdata={"wells": {}})
        grid_reader = MagicMock()
        property_reader = MagicMock()
        monkeypatch.setattr(xtgeo, "grid_from_file", grid_reader)
        monkeypatch.setattr(xtgeo, "gridproperty_from_file", property_reader)

        xapp.load_grid()

        grid_reader.assert_not_called()
        property_reader.assert_not_called()


class TestXsectPlotting:
    """End-to-end tests for supported Python plotting inputs."""

    def test_parse_config_file_overrides_defaults(self, tmp_path):
        config_file = tmp_path / "xsect.yml"
        config_file.write_text(
            "input:\n  wells:\n    zonelog: CUSTOM_ZONE\n", encoding="utf-8"
        )
        xapp = _Xsections(inputdata={"wells": {}})
        xapp.args = SimpleNamespace(config=str(config_file))

        xapp.parse_config()

        assert xapp.config["input"]["wells"]["zonelog"] == "CUSTOM_ZONE"

    def test_parse_config_rejects_missing_file(self, tmp_path):
        xapp = _Xsections(inputdata={"wells": {}})
        xapp.args = SimpleNamespace(config=str(tmp_path / "missing.yml"))

        with pytest.raises(OSError, match="No such config file exists"):
            xapp.parse_config()

    def test_parse_args_exits_without_required_arguments(self):
        xapp = _Xsections(inputdata={"wells": {}})
        xapp.args = []

        with pytest.raises(SystemExit):
            xapp.parse_args()

    def test_plot_from_paths(self, testdir, tmp_path):
        """Make plots using file paths from Python input."""
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

        xsectplot(inputdata=inputs, plotsettings=psettings, output=outputs)
        assert (tmp_path / "55_33-A-4.png").is_file()


class TestXsectPlottingHelpers:
    """Tests for plotting helpers and optional rendering branches."""

    def test_plotting_skips_well_without_fence(self, monkeypatch, tmp_path):
        settings = _XsectSettings()
        settings.output_plotfolder = str(tmp_path / "plots")
        well = SimpleNamespace(name="well-1")
        app = SimpleNamespace(
            plotsettings=settings,
            wells={"wlist": [well]},
            surfaces={"primary": [], "contacts": [], "secondary": []},
            outline=None,
            cube=None,
            grid=None,
            gridproperty=None,
        )
        xplot = MagicMock()
        xplot.fence = None
        monkeypatch.setattr(plotting_helpers, "XSection", MagicMock(return_value=xplot))
        save_fig = MagicMock()
        monkeypatch.setattr(plotting_helpers, "_save_fig", save_fig)

        plotting_helpers._plotting_mpl(app, settings)

        save_fig.assert_not_called()
        xplot.canvas.assert_not_called()

    def test_plotting_includes_overlays_and_crossings(self, monkeypatch, tmp_path):
        settings = _XsectSettings()
        settings.output_plotfolder = str(tmp_path / "plots")
        settings.design_zrange = {"well-1": (100, 200)}
        settings.cube_range = [0.0, 1.0]
        settings.grid_range = [-1.0, 1.0]
        settings.grid_colors = "rainbow"
        settings.grid_alpha = 0.8
        settings.grid_zinc = 0.5
        settings.wells_wellcrossings_show = "crossings.csv"
        well = SimpleNamespace(name="well-1", xwellname="well-1", wellname="well-1")
        app = SimpleNamespace(
            plotsettings=settings,
            wells={
                "wlist": [well],
                "zonelog": "Zone",
                "facieslog": None,
                "perflog": None,
            },
            surfaces={
                "primary": [object()],
                "contacts": [object()],
                "secondary": [object()],
            },
            outline=None,
            cube=object(),
            grid=object(),
            gridproperty=object(),
        )
        xplot = MagicMock()
        xplot.fence = object()
        crossings = pd.DataFrame({"WELL": ["well-1", "other"], "X": [1, 2]})
        monkeypatch.setattr(plotting_helpers, "XSection", MagicMock(return_value=xplot))
        monkeypatch.setattr(
            plotting_helpers.pd, "read_csv", MagicMock(return_value=crossings)
        )
        monkeypatch.setattr(
            plotting_helpers, "_save_fig", MagicMock(return_value="plot.png")
        )
        monkeypatch.setattr(plotting_helpers, "_collect_pdf", MagicMock())

        plotting_helpers._plotting_mpl(app, settings)

        xplot.plot_cube.assert_called_once()
        xplot.plot_grid3d.assert_called_once()
        assert xplot.plot_surfaces.call_count == 4
        assert xplot.plot_map.called
        assert xplot.plot_wellmap.called
        wellcrossings = xplot.plot_well.call_args.kwargs["wellcrossings"]
        assert wellcrossings.to_dict("list") == {"X": [1]}

    def test_save_fig_builds_path_and_shows_when_requested(self, monkeypatch, tmp_path):
        settings = SimpleNamespace(
            output_prefix="prefix_",
            output_plotfolder=str(tmp_path),
            output_format="png",
            design_dpi=150,
        )
        well = SimpleNamespace(xwellname="well-1", wellname="well-1")
        xplot = MagicMock()
        monkeypatch.setenv("XTG_SHOW", "1")

        result = plotting_helpers._save_fig(well, settings, xplot)

        assert result == str(tmp_path / "prefix_well-1.png")
        xplot.savefig.assert_called_once_with(result, fformat="png", dpi=150)
        xplot.show.assert_called_once()

    def test_compute_wellcrossings_disabled(self):
        settings = SimpleNamespace(wells_wellcrossings_show=False)

        assert plotting_helpers._compute_wellcrossings(settings) is None

    def test_compute_wellcrossings_rejects_unsupported_compute_mode(self):
        settings = SimpleNamespace(wells_wellcrossings_show=True)

        with pytest.raises(NotImplementedError, match="not supported yet"):
            plotting_helpers._compute_wellcrossings(settings)

    def test_plot_with_preloaded_objects(self, testdir, tmp_path):
        """Make plots using preloaded well and surface objects."""
        wells = ["55_33-A-1.rmswell", "55_33-A-4.rmswell"]
        surfaces = [
            "01_topvolantis.gri",
            "02_toptherys.gri",
            "03_topvolon.gri",
            "04_basevolantis.gri",
        ]

        wlist = [xtgeo.well_from_file(testdir / WELLSET1 / well) for well in wells]
        slist = [
            xtgeo.surface_from_file(testdir / SURFACESET1 / surf) for surf in surfaces
        ]

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

        xsectplot(inputdata=inputs, plotsettings=psettings, output=outputs)
        assert (tmp_path / "55_33-A-4.png").is_file()

    def test_plot_with_cube(self, testdir, tmp_path):
        """Make plots with a preloaded cube and custom depth ranges."""
        wells = ["55_33-A-4.rmswell"]
        surfaces = [
            "01_topvolantis.gri",
            "02_toptherys.gri",
            "03_topvolon.gri",
            "04_basevolantis.gri",
        ]

        wlist = [xtgeo.well_from_file(testdir / WELLSET1 / well) for well in wells]
        slist = [
            xtgeo.surface_from_file(testdir / SURFACESET1 / surf) for surf in surfaces
        ]
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
                    "55_33.*": [1450, 1750],
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

        xsectplot(inputdata=inputs, plotsettings=psettings, output=outputs)
        assert (tmp_path / "55_33-A-4.png").is_file()
