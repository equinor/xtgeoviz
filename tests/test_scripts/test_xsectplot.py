"""Module for testing stand-alone scripts and/or entrypoints functions."""

import os
import pathlib
from argparse import Namespace
from types import SimpleNamespace
from typing import Any, cast
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


def _config_app(
    zrange: Any,
    primary: list[SimpleNamespace],
    wells: list[SimpleNamespace] | None = None,
    cube: Any = None,
    grid: Any = None,
    gridproperty: Any = None,
) -> SimpleNamespace:
    """Build a minimal application-like object for config completion tests.

    Args:
        zrange: Configured depth range or smart-range mode.
        primary: Primary surface stand-ins used to derive depth ranges.
        wells: Optional well stand-ins used for per-well ranges.
        cube: Optional cube stand-in used to derive a value range.
        grid: Optional grid stand-in that enables grid range completion.
        gridproperty: Optional property stand-in supplying grid values.

    Returns:
        A namespace with the config and loaded-data attributes used by
        ``config_complete``.
    """
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

    def test_defaults(self) -> None:
        """Config defaults are available as YAML and a Python mapping."""
        yamlresult = config_defaults()
        assert isinstance(yamlresult, str)

        dictresult = config_defaults(as_yaml=False)
        assert isinstance(dictresult, dict)
        assert dictresult["input"]["wells"]["zonelog"] == "ZONELOG"

    def test_dict_merge_ok(self) -> None:
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

    def test_dict_merge_rejects_invalid_top_level_key(self) -> None:
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

    def test_dict_merge_rejects_invalid_nested_key(self) -> None:
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

    def test_dict_merge_appends_lists_and_replaces_scalars(self) -> None:
        """List values extend while scalar settings are overridden."""
        defaults = {"settings": {"values": [1, 2], "label": "default"}}
        userinput = {"settings": {"values": [3], "label": "custom"}}

        merged = data_merge(defaults, userinput)

        assert merged == {"settings": {"values": [1, 2, 3], "label": "custom"}}

    def test_dict_merge_appends_scalar_to_list(self) -> None:
        """A scalar override is appended when the existing value is a list."""
        defaults = {"settings": {"values": [1, 2]}}

        merged = data_merge(defaults, {"settings": {"values": 3}})

        assert merged == {"settings": {"values": [1, 2, 3]}}

    def test_dict_merge_rejects_non_dict_nested_value(self) -> None:
        """A mapping cannot be replaced with a scalar during recursive merging."""
        with pytest.raises(ConfigError, match="Cannot merge non-dict"):
            data_merge({"settings": {"value": 1}}, {"settings": "invalid"})

    def test_dict_merge_rejects_unsupported_superset(self) -> None:
        """Unsupported value types are rejected instead of silently discarded."""
        with pytest.raises(ConfigError, match="NOT IMPLEMENTED"):
            data_merge((1, 2), {})

    @pytest.mark.parametrize("superset", [None, "default", 10, 2.5])
    def test_dict_merge_replaces_scalar_superset(self, superset: Any) -> None:
        """Null and scalar defaults are replaced by the supplied value."""
        subset = {"replacement": True}

        assert data_merge(superset, subset) is subset

    def test_settings_class_defaults(self) -> None:
        """The plot settings object starts with documented defaults."""
        settings = _XsectSettings()

        assert settings.design_dpi == 100
        assert settings.wells_zonelog_zoneshift == 0

    def test_config_complete_calculates_smart0_range(self) -> None:
        """Smart0 expands the first and last surface elevations by ten units."""
        primary = [
            SimpleNamespace(values=np.array([1234.0, 1300.0])),
            SimpleNamespace(values=np.array([1700.0, 1788.0])),
        ]
        app = _config_app("smart0", primary)

        config_complete(cast("_Xsections", app))

        assert app.config["plotsettings"]["design"]["zrange"] == [1220, 1800]
        assert app.config["plotsettings"]["wells"]["zonelog"]["colordict"] == {
            value: value for value in range(100)
        }

    def test_config_complete_defaults_empty_range_to_smart0(self) -> None:
        """An empty configured range selects smart0."""
        primary = [
            SimpleNamespace(values=np.array([1234.0])),
            SimpleNamespace(values=np.array([1788.0])),
        ]
        app = _config_app("", primary)

        config_complete(cast("_Xsections", app))

        assert app.config["plotsettings"]["design"]["zrange"] == [1220, 1800]

    def test_config_complete_caps_smart1_range_to_wells(self) -> None:
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

        config_complete(cast("_Xsections", app))

        assert app.config["plotsettings"]["design"]["zrange"] == [1220, 1510]

    def test_config_complete_applies_per_well_regex_ranges(self) -> None:
        """User regex ranges override the global default for matching wells."""
        primary: list[SimpleNamespace] = []
        wells = [
            SimpleNamespace(name="55_33-1"),
            SimpleNamespace(name="other-well"),
        ]
        app = _config_app(
            {"default": [1000, 2000], "55_33.*": [1450, 1750]},
            primary,
            wells=wells,
        )

        config_complete(cast("_Xsections", app))

        assert app.config["plotsettings"]["design"]["zrange"] == {
            "55_33-1": [1450, 1750],
            "other-well": [1000, 2000],
        }

    def test_config_complete_uses_cube_and_grid_ranges(self) -> None:
        """Unset cube and grid ranges are derived from their property values."""
        app = _config_app(
            [1000, 2000],
            [],
            cube=SimpleNamespace(values=np.array([-2.0, 5.0])),
            grid=SimpleNamespace(),
            gridproperty=SimpleNamespace(values=np.array([10.0, 40.0])),
        )

        config_complete(cast("_Xsections", app))

        assert app.config["plotsettings"]["cube"]["range"] == [-2.0, 5.0]
        assert app.config["plotsettings"]["grid"]["range"] == [10.0, 40.0]

    def test_config_complete_rejects_unknown_zrange_mode(self) -> None:
        """Unsupported range values fail with an actionable error."""
        app = _config_app(object(), [])

        with pytest.raises(RuntimeError, match="Cannot process/understand the zrange"):
            config_complete(cast("_Xsections", app))


class TestXsectInputLoading:
    """Tests for loading inputs into the cross-section app."""

    def test_load_wells_rejects_empty_folder(self, tmp_path: pathlib.Path) -> None:
        """Reject a well folder with no files matching the configured pattern.

        Args:
            tmp_path: Temporary empty directory used as the well source.
        """
        inputs = {
            "wells": {
                "folder": str(tmp_path),
                "wildcard": "*.rmswell",
            }
        }
        xapp = _Xsections(inputdata=inputs)

        with pytest.raises(SystemExit, match="Cannot plot, no wells as input"):
            xapp.load_wells()

    def test_load_preloaded_wells_and_optional_logs(self) -> None:
        """Use preloaded wells and preserve optional facies and perf logs."""
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

    def test_load_wells(self, testdir: pathlib.Path) -> None:
        """Load matching well files from the XTGeo test-data directory.

        Args:
            testdir: Root directory containing the well fixtures.
        """
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

    def test_load_surfaces(self, testdir: pathlib.Path) -> None:
        """Load primary surfaces and apply their configured display names.

        Args:
            testdir: Root directory containing the surface fixtures.
        """
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

    def test_load_surfaces_uses_default_names(self, testdir: pathlib.Path) -> None:
        """Assign sequential names when no surface names are configured.

        Args:
            testdir: Root directory containing the surface fixtures.
        """
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

    def test_load_surfaces_rejects_non_xtgeo_objects(self) -> None:
        """Reject preloaded surface values that are not XTGeo surfaces."""
        inputs = {"surfaces": {"primary": {"objects": [object()]}}}
        xapp = _Xsections(inputdata=inputs)

        with pytest.raises(RuntimeError, match="Surface object are not XTGeo objects"):
            xapp.load_surfaces()

    def test_load_outline_from_preloaded_object(self, testdir: pathlib.Path) -> None:
        """Keep a preloaded polygons object as the field outline.

        Args:
            testdir: Root directory containing the polygon fixture.
        """
        outline = xtgeo.polygons_from_file(testdir / OUTLINE)
        xapp = _Xsections(inputdata={"outline": outline})

        xapp.load_outline()

        assert xapp.outline is outline

    def test_load_cube_from_path(self, testdir: pathlib.Path) -> None:
        """Read a cube from its configured file path.

        Args:
            testdir: Root directory containing the cube fixture.
        """
        xapp = _Xsections(inputdata={"cube": str(testdir / CUBE)})

        xapp.load_cube()

        assert isinstance(xapp.cube, xtgeo.Cube)

    def test_load_missing_cube_sets_none(self) -> None:
        """Leave the application cube unset when no cube is configured."""
        xapp = _Xsections(inputdata={"wells": {}})

        xapp.load_cube()

        assert xapp.cube is None

    @pytest.mark.parametrize("fromgrid", [None, "geometry.roff"])
    def test_load_grid_property_and_optional_geometry(
        self, monkeypatch: pytest.MonkeyPatch, fromgrid: str | None
    ) -> None:
        """Read grid properties and skip geometry when supplied by surfaces.

        Args:
            monkeypatch: Replaces XTGeo readers with test doubles.
            fromgrid: Geometry source already associated with surfaces, if any.
        """
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

    def test_load_grid_without_complete_inputs_does_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Skip grid reads when geometry and property paths are incomplete.

        Args:
            monkeypatch: Replaces XTGeo readers to assert they are not called.
        """
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

    def test_parse_config_file_overrides_defaults(self, tmp_path: pathlib.Path) -> None:
        """Merge a YAML file override while retaining default settings.

        Args:
            tmp_path: Temporary directory used to create the YAML config file.
        """
        config_file = tmp_path / "xsect.yml"
        config_file.write_text(
            "input:\n  wells:\n    zonelog: CUSTOM_ZONE\n", encoding="utf-8"
        )
        xapp = _Xsections(inputdata={"wells": {}})
        xapp.args = Namespace(config=str(config_file))

        xapp.parse_config()

        assert xapp.config["input"]["wells"]["zonelog"] == "CUSTOM_ZONE"

    def test_parse_config_rejects_missing_file(self, tmp_path: pathlib.Path) -> None:
        """Raise an error when the requested YAML config file is missing.

        Args:
            tmp_path: Temporary directory used to construct a missing path.
        """
        xapp = _Xsections(inputdata={"wells": {}})
        xapp.args = Namespace(config=str(tmp_path / "missing.yml"))

        with pytest.raises(OSError, match="No such config file exists"):
            xapp.parse_config()

    def test_parse_args_exits_without_required_arguments(self) -> None:
        """Exit with usage information when command-line arguments are absent."""
        xapp = _Xsections(inputdata={"wells": {}})
        xapp.args = []

        with pytest.raises(SystemExit):
            xapp.parse_args()

    @pytest.mark.parametrize("equals_syntax", [False, True])
    def test_explicit_args_load_configuration(
        self, tmp_path: pathlib.Path, equals_syntax: bool
    ) -> None:
        """Use explicit command-line arguments to load the selected YAML file.

        Args:
            tmp_path: Temporary directory used for the config path.
            equals_syntax: Whether to pass the option and path as one argument.
        """
        config_file = tmp_path / "xsect.yml"
        config_file.write_text(
            "input:\n  wells:\n    zonelog: CLI_ZONE\n", encoding="utf-8"
        )
        args = (
            [f"--config={config_file}"]
            if equals_syntax
            else ["--config", str(config_file)]
        )
        xapp = _Xsections(args=args)

        assert isinstance(xapp.args, Namespace)
        assert xapp.args.config == str(config_file)
        assert xapp.config["input"]["wells"]["zonelog"] == "CLI_ZONE"

    def test_plot_from_paths(
        self, testdir: pathlib.Path, tmp_path: pathlib.Path
    ) -> None:
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

    def test_plotting_skips_well_without_fence(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """Skip rendering and saving when XTGeo produces no fence.

        Args:
            monkeypatch: Replaces the cross-section constructor and save helper.
            tmp_path: Temporary output directory for the plot.
        """
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

        plotting_helpers._plotting_mpl(cast("_Xsections", app), settings)

        save_fig.assert_not_called()
        xplot.canvas.assert_not_called()

    def test_plotting_includes_overlays_and_crossings(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """Render overlays and pass only the current well's crossing rows.

        Args:
            monkeypatch: Replaces XTGeo plotting and CSV-reading dependencies.
            tmp_path: Temporary output directory for the plot.
        """
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

        plotting_helpers._plotting_mpl(cast("_Xsections", app), settings)

        xplot.plot_cube.assert_called_once()
        xplot.plot_grid3d.assert_called_once()
        assert xplot.plot_surfaces.call_count == 4
        assert xplot.plot_map.called
        assert xplot.plot_wellmap.called
        wellcrossings = xplot.plot_well.call_args.kwargs["wellcrossings"]
        assert wellcrossings.to_dict("list") == {"X": [1]}

    def test_save_fig_builds_path_and_shows_when_requested(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """Apply the output prefix and display the plot when XTG_SHOW is set.

        Args:
            monkeypatch: Sets the environment variable and isolates the plot.
            tmp_path: Temporary destination directory.
        """
        settings = SimpleNamespace(
            output_prefix="prefix_",
            output_plotfolder=str(tmp_path),
            output_format="png",
            design_dpi=150,
        )
        well = SimpleNamespace(xwellname="well-1", wellname="well-1")
        xplot = MagicMock()
        monkeypatch.setenv("XTG_SHOW", "1")

        result = plotting_helpers._save_fig(
            well, cast("_XsectSettings", settings), xplot
        )

        assert result == str(tmp_path / "prefix_well-1.png")
        xplot.savefig.assert_called_once_with(result, fformat="png", dpi=150)
        xplot.show.assert_called_once()

    def test_create_or_clean_folder_creates_output_directory(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Create the configured output directory when it does not exist.

        Args:
            tmp_path: Temporary parent directory for plot output.
        """
        output_folder = tmp_path / "new-plots"
        settings = SimpleNamespace(
            output_plotfolder=str(output_folder), output_cleanup=False
        )

        plotting_helpers._create_or_clean_folder(cast("_XsectSettings", settings))

        assert output_folder.is_dir()

    def test_create_or_clean_folder_cleans_files_and_subdirectories(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Remove existing files and nested directories when cleanup is enabled.

        Args:
            tmp_path: Temporary parent directory containing stale plot output.
        """
        output_folder = tmp_path / "plots"
        nested_folder = output_folder / "old-run"
        nested_folder.mkdir(parents=True)
        (output_folder / "old.png").touch()
        (nested_folder / "old.png").touch()
        settings = SimpleNamespace(
            output_plotfolder=str(output_folder), output_cleanup=True
        )

        plotting_helpers._create_or_clean_folder(cast("_XsectSettings", settings))

        assert list(output_folder.iterdir()) == []

    def test_create_or_clean_folder_unlinks_directory_symlinks(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Remove a directory symlink without deleting its target contents."""
        output_folder = tmp_path / "plots"
        output_folder.mkdir()
        target_folder = tmp_path / "preserved"
        target_folder.mkdir()
        sentinel = target_folder / "keep.txt"
        sentinel.touch()
        directory_link = output_folder / "linked-output"
        try:
            directory_link.symlink_to(target_folder, target_is_directory=True)
        except (NotImplementedError, OSError) as error:
            pytest.skip(f"Directory symlinks are unavailable: {error}")

        settings = SimpleNamespace(
            output_plotfolder=str(output_folder), output_cleanup=True
        )

        plotting_helpers._create_or_clean_folder(cast("_XsectSettings", settings))

        assert not directory_link.is_symlink()
        assert sentinel.is_file()

    @pytest.mark.parametrize("trailing_separator", [False, True])
    def test_create_or_clean_folder_rejects_symlinked_output_root(
        self, tmp_path: pathlib.Path, trailing_separator: bool
    ) -> None:
        """Refuse cleanup when the output folder itself is a symlink.

        Args:
            tmp_path: Temporary parent directory for the symlink and its target.
            trailing_separator: Whether to append a separator to the symlink path.
        """
        target_folder = tmp_path / "preserved"
        target_folder.mkdir()
        sentinel = target_folder / "keep.txt"
        sentinel.touch()
        output_folder = tmp_path / "plots"
        try:
            output_folder.symlink_to(target_folder, target_is_directory=True)
        except (NotImplementedError, OSError) as error:
            pytest.skip(f"Directory symlinks are unavailable: {error}")

        output_path = str(output_folder)
        if trailing_separator:
            output_path += os.sep
        settings = SimpleNamespace(output_plotfolder=output_path, output_cleanup=True)

        with pytest.raises(OSError, match="symlinked output folder"):
            plotting_helpers._create_or_clean_folder(cast("_XsectSettings", settings))

        assert sentinel.is_file()

    def test_create_or_clean_folder_rejects_shared_tmp(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Refuse to clean the shared temporary directory."""
        directory_listing = MagicMock(
            side_effect=AssertionError("must reject /tmp before listing it")
        )
        monkeypatch.setattr(plotting_helpers.os, "listdir", directory_listing)
        settings = SimpleNamespace(output_plotfolder="/tmp", output_cleanup=True)

        with pytest.raises(OSError, match="shared /tmp output folder"):
            plotting_helpers._create_or_clean_folder(cast("_XsectSettings", settings))

        directory_listing.assert_not_called()

    def test_plotting_rejects_cleanup_that_overlaps_well_folder(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Refuse cleanup when the configured well folder overlaps output.

        Args:
            tmp_path: Temporary parent for the output and well input folders.
        """
        output_folder = tmp_path / "plots"
        well_folder = output_folder / "wells"
        well_folder.mkdir(parents=True)
        sentinel = well_folder / "well.w"
        sentinel.touch()
        settings = _XsectSettings(
            output_plotfolder=str(output_folder), output_cleanup=True
        )
        x_sections = _Xsections(inputdata={"wells": {"folder": str(well_folder)}})

        with pytest.raises(OSError, match="overlapping configured input"):
            plotting_helpers._plotting_mpl(x_sections, settings)

        assert sentinel.is_file()

    def test_plotting_rejects_cleanup_that_overlaps_surface_folder(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """Refuse cleanup when a configured surface folder is inside output.

        Args:
            monkeypatch: Spies on output-folder enumeration.
            tmp_path: Temporary parent for output and surface input folders.
        """
        output_folder = tmp_path / "plots"
        surface_folder = output_folder / "surfaces"
        surface_folder.mkdir(parents=True)
        sentinel = surface_folder / "surface.gri"
        sentinel.touch()
        directory_listing = MagicMock(return_value=[])
        monkeypatch.setattr(plotting_helpers.os, "listdir", directory_listing)
        settings = _XsectSettings(
            output_plotfolder=str(output_folder), output_cleanup=True
        )
        x_sections = _Xsections(
            inputdata={"surfaces": {"primary": {"folder": str(surface_folder)}}}
        )

        with pytest.raises(OSError, match="overlapping configured input"):
            plotting_helpers._plotting_mpl(x_sections, settings)

        directory_listing.assert_not_called()
        assert sentinel.is_file()

    def test_plotting_rejects_pdf_collision_before_saving_wells(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """Reject joined-PDF collisions before cleanup or per-well saves.

        Args:
            monkeypatch: Replaces folder cleanup with a spy.
            tmp_path: Temporary output directory for the predicted PDF paths.
        """
        settings = _XsectSettings(
            output_plotfolder=str(tmp_path),
            output_format="pdf",
            output_pdfjoin="well-1.pdf",
        )
        x_sections = _Xsections(inputdata={"wells": {}})
        x_sections.wells["wlist"] = [SimpleNamespace(xwellname="well-1")]
        folder_cleanup = MagicMock()
        monkeypatch.setattr(plotting_helpers, "_create_or_clean_folder", folder_cleanup)

        with pytest.raises(ValueError, match="overlaps a source PDF"):
            plotting_helpers._plotting_mpl(x_sections, settings)

        folder_cleanup.assert_not_called()

    @pytest.mark.parametrize("nested", [False, True])
    def test_create_or_clean_folder_rejects_wellcrossings_input(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: pathlib.Path,
        nested: bool,
    ) -> None:
        """Reject cleanup when the configured well-crossings CSV is inside it.
        )

                tmp_path: Temporary parent for output and input files.
                nested: Whether to place the input CSV in a subdirectory.
        """
        output_folder = tmp_path / "plots"
        input_folder = output_folder / "nested" if nested else output_folder
        input_folder.mkdir(parents=True)
        crossings_file = input_folder / "crossings.csv"
        crossings_file.write_text("WELL,VALUE\nwell-1,1\n", encoding="utf-8")
        directory_listing = MagicMock()
        monkeypatch.setattr(plotting_helpers.os, "listdir", directory_listing)
        settings = _XsectSettings(
            output_plotfolder=str(output_folder),
            output_cleanup=True,
            wells_wellcrossings_show=str(crossings_file),
        )

        with pytest.raises(OSError, match="well-crossings CSV"):
            plotting_helpers._create_or_clean_folder(settings)

        directory_listing.assert_not_called()
        assert crossings_file.is_file()

    def test_create_or_clean_folder_keeps_external_wellcrossings_input(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Allow cleanup when the well-crossings CSV is outside the output tree.

        Args:
            tmp_path: Temporary parent for output and the external input CSV.
        """
        output_folder = tmp_path / "plots"
        output_folder.mkdir()
        stale_plot = output_folder / "old.svg"
        stale_plot.touch()
        crossings_file = tmp_path / "crossings.csv"
        crossings_file.write_text("WELL,VALUE\nwell-1,1\n", encoding="utf-8")
        settings = _XsectSettings(
            output_plotfolder=str(output_folder),
            output_cleanup=True,
            wells_wellcrossings_show=str(crossings_file),
        )

        plotting_helpers._create_or_clean_folder(settings)

        assert not stale_plot.exists()
        assert crossings_file.is_file()

    def test_create_or_clean_folder_resolves_symlinked_wellcrossings_path(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Resolve symlinks before evaluating parent-directory components.

        Args:
            tmp_path: Temporary parent for the output and symlink paths.
        """
        output_folder = tmp_path / "plots"
        nested_folder = output_folder / "nested"
        nested_folder.mkdir(parents=True)
        crossings_file = output_folder / "crossings.csv"
        crossings_file.write_text("WELL,VALUE\nwell-1,1\n", encoding="utf-8")
        linked_folder = tmp_path / "linked-nested"
        try:
            linked_folder.symlink_to(nested_folder, target_is_directory=True)
        except (NotImplementedError, OSError) as error:
            pytest.skip(f"Directory symlinks are unavailable: {error}")
        configured_path = linked_folder / ".." / crossings_file.name
        settings = _XsectSettings(
            output_plotfolder=str(output_folder),
            output_cleanup=True,
            wells_wellcrossings_show=str(configured_path),
        )

        with pytest.raises(OSError, match="well-crossings CSV"):
            plotting_helpers._create_or_clean_folder(settings)

        assert crossings_file.is_file()

    @pytest.mark.parametrize(
        "output_folder", ["/", ".", "..", str(pathlib.Path.home())]
    )
    def test_create_or_clean_folder_rejects_unsafe_ancestors(
        self,
        monkeypatch: pytest.MonkeyPatch,
        output_folder: str,
    ) -> None:
        """Refuse cleanup of roots and directories containing user data."""
        directory_listing = MagicMock()
        monkeypatch.setattr(plotting_helpers.os, "listdir", directory_listing)
        settings = _XsectSettings(output_plotfolder=output_folder, output_cleanup=True)

        with pytest.raises(OSError, match="unsafe output folder"):
            plotting_helpers._create_or_clean_folder(settings)

        directory_listing.assert_not_called()

    def test_compute_wellcrossings_disabled(self) -> None:
        """Return None when well-crossing input is disabled."""
        settings = SimpleNamespace(wells_wellcrossings_show=False)

        assert (
            plotting_helpers._compute_wellcrossings(cast("_XsectSettings", settings))
            is None
        )

    def test_compute_wellcrossings_rejects_unsupported_compute_mode(self) -> None:
        """Reject enabled crossings when no CSV path is supplied."""
        settings = SimpleNamespace(wells_wellcrossings_show=True)

        with pytest.raises(NotImplementedError, match="not supported yet"):
            plotting_helpers._compute_wellcrossings(cast("_XsectSettings", settings))

    @pytest.mark.parametrize("output_format", ["png", "pdf"])
    def test_collect_pdf_returns_without_joining(
        self, monkeypatch: pytest.MonkeyPatch, output_format: str
    ) -> None:
        """Skip Ghostscript when output is not joined PDF.

        Args:
            monkeypatch: Replaces the subprocess call with a spy.
            output_format: Format parameterized between PNG and PDF.
        """
        settings = SimpleNamespace(output_format=output_format, output_pdfjoin=False)
        subprocess_call = MagicMock()
        monkeypatch.setattr(plotting_helpers.subprocess, "call", subprocess_call)

        plotting_helpers._collect_pdf(cast("_XsectSettings", settings), ["plot.pdf"])

        subprocess_call.assert_not_called()

    def test_collect_pdf_joins_files_and_removes_parts(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """Join per-well PDFs and remove the source files after success.

        Args:
            monkeypatch: Replaces Ghostscript and file removal with spies.
            tmp_path: Temporary output directory for the joined PDF.
        """
        output_folder = tmp_path / "plots with spaces"
        plot_files = [
            str(output_folder / "one plot.pdf"),
            str(output_folder / "two plot.pdf"),
        ]
        settings = SimpleNamespace(
            output_format="pdf",
            output_pdfjoin="joined plots.pdf",
            output_plotfolder=str(output_folder),
        )
        subprocess_call = MagicMock(return_value=0)
        removed_files: list[str] = []
        monkeypatch.setattr(plotting_helpers.subprocess, "call", subprocess_call)
        monkeypatch.setattr(plotting_helpers.os, "remove", removed_files.append)

        plotting_helpers._collect_pdf(cast("_XsectSettings", settings), plot_files)

        command = subprocess_call.call_args.args[0]
        assert command == [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/default",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dDetectDuplicateImages",
            "-dCompressFonts=true",
            "-r150",
            f"-sOutputFile={output_folder / 'joined plots.pdf'}",
            *plot_files,
        ]
        assert subprocess_call.call_args.kwargs == {"shell": False}
        assert removed_files == plot_files

    @pytest.mark.parametrize(
        "output_pdfjoin", ["one plot.pdf", "nested/../one plot.pdf"]
    )
    def test_collect_pdf_rejects_destination_that_overlaps_source(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: pathlib.Path,
        output_pdfjoin: str,
    ) -> None:
        """Reject a joined PDF destination that resolves to an input file.

        Args:
            monkeypatch: Replaces Ghostscript and file removal with spies.
            tmp_path: Temporary parent for the output and source paths.
            output_pdfjoin: Joined filename, including a normalized path variant.
        """
        output_folder = tmp_path / "plots"
        source_pdf = output_folder / "one plot.pdf"
        settings = _XsectSettings(
            output_format="pdf",
            output_pdfjoin=output_pdfjoin,
            output_plotfolder=str(output_folder),
        )
        subprocess_call = MagicMock(return_value=0)
        removed_files: list[str] = []
        monkeypatch.setattr(plotting_helpers.subprocess, "call", subprocess_call)
        monkeypatch.setattr(plotting_helpers.os, "remove", removed_files.append)

        with pytest.raises(ValueError, match="overlaps a source PDF"):
            plotting_helpers._collect_pdf(settings, [str(source_pdf)])

        subprocess_call.assert_not_called()
        assert removed_files == []

    def test_collect_pdf_rejects_hard_link_to_source(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """Reject a joined destination that is a hard link to an input PDF.

        Args:
            monkeypatch: Replaces Ghostscript and file removal with spies.
            tmp_path: Temporary directory for the linked source and destination.
        """
        output_folder = tmp_path / "plots"
        output_folder.mkdir()
        source_pdf = output_folder / "source.pdf"
        source_pdf.write_bytes(b"source PDF")
        joined_pdf = output_folder / "joined.pdf"
        try:
            joined_pdf.hardlink_to(source_pdf)
        except (NotImplementedError, OSError) as error:
            pytest.skip(f"Hard links are unavailable: {error}")

        settings = _XsectSettings(
            output_format="pdf",
            output_pdfjoin=joined_pdf.name,
            output_plotfolder=str(output_folder),
        )
        subprocess_call = MagicMock(return_value=0)
        removed_files: list[str] = []
        monkeypatch.setattr(plotting_helpers.subprocess, "call", subprocess_call)
        monkeypatch.setattr(plotting_helpers.os, "remove", removed_files.append)

        with pytest.raises(ValueError, match="overlaps a source PDF"):
            plotting_helpers._collect_pdf(settings, [str(source_pdf)])

        subprocess_call.assert_not_called()
        assert removed_files == []
        assert source_pdf.read_bytes() == b"source PDF"

    def test_collect_pdf_raises_when_ghostscript_fails(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """Raise an error when Ghostscript reports a failed PDF join.

        Args:
            monkeypatch: Makes the subprocess call return a failure status.
            tmp_path: Temporary output directory for the joined PDF.
        """
        settings = SimpleNamespace(
            output_format="pdf",
            output_pdfjoin="joined.pdf",
            output_plotfolder=str(tmp_path),
        )
        monkeypatch.setattr(
            plotting_helpers.subprocess, "call", MagicMock(return_value=1)
        )

        with pytest.raises(
            RuntimeError, match="Received number != 0 from subprosess: 1"
        ):
            plotting_helpers._collect_pdf(cast("_XsectSettings", settings), ["one.pdf"])

    def test_plot_with_preloaded_objects(
        self, testdir: pathlib.Path, tmp_path: pathlib.Path
    ) -> None:
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

    def test_plot_with_cube(
        self, testdir: pathlib.Path, tmp_path: pathlib.Path
    ) -> None:
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
