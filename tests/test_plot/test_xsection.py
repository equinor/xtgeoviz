import glob
import pathlib
from os.path import join
from types import SimpleNamespace
from unittest.mock import MagicMock

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import xtgeo
from matplotlib.collections import LineCollection

from xtgeoviz.plot import XSection, _libwrapper

TPATH = pathlib.Path("../xtgeo-testdata")

USEFILE1 = TPATH / "wells/reek/1/OP_1.w"
USEFILE2 = TPATH / "surfaces/reek/1/topreek_rota.gri"
USEFILE3 = TPATH / "polygons/reek/1/mypoly.pol"
USEFILE4 = TPATH / "wells/reek/1/OP_5.w"
USEFILE5 = TPATH / "surfaces/reek/2/*.gri"
USEFILE6 = TPATH / "cubes/reek/syntseis_20000101_seismic_depth_stack.segy"

USEFILE7 = TPATH / "wells/reek/1/OP_2.w"


class TestXSection:
    """Tests for cross-section plotting."""

    @pytest.mark.parametrize(
        ("matplotlib_version", "combined_labels"),
        [("3.3.2", False), ("3.5.0", True)],
    )
    def test_matplotlib_set_xticks_uses_compatibility_api(
        self, monkeypatch, matplotlib_version, combined_labels
    ):
        """Use the tick-label API supported by the installed Matplotlib version."""
        monkeypatch.setattr(_libwrapper.matplotlib, "__version__", matplotlib_version)
        axes = MagicMock()
        ticks = [0.0, 50.0, 100.0]
        labels = ["1200", "1250", "1300"]

        _libwrapper.matplotlib_set_xticks(axes, ticks, labels)

        if combined_labels:
            axes.set_xticks.assert_called_once_with(ticks, labels=labels)
            axes.set_xticklabels.assert_not_called()
        else:
            axes.set_xticks.assert_called_once_with(ticks)
            axes.set_xticklabels.assert_called_once_with(labels)

    def test_xsection_init(self):
        """Trigger XSection class, basically."""
        xsect = XSection()
        assert xsect.pagesize == "A4"

    def test_simple_plot(self, tmpdir, show_plot, generate_plot):
        """Test as simple XSECT plot."""
        mywell = xtgeo.well_from_file(USEFILE4)
        mysurfaces = []
        mysurf = xtgeo.surface_from_file(USEFILE2)

        for i in range(10):
            xsurf = mysurf.copy()
            xsurf.values = xsurf.values + i * 20
            xsurf.name = f"Surface_{i}"
            mysurfaces.append(xsurf)

        myplot = XSection(zmin=1500, zmax=1800, well=mywell, surfaces=mysurfaces)

        clist = [0, 1, 222, 3, 5, 7, 3, 12, 11, 10, 9, 8]
        cfil1 = "xtgeo"
        cfil2 = TPATH / "etc/colortables/colfacies.txt"

        assert 222 in clist
        assert "xtgeo" in cfil1
        assert "colfacies" in str(cfil2)

        myplot.colormap = cfil1
        myplot.canvas(title="Manamana", subtitle="My Dear Well")
        myplot.plot_surfaces(fill=False)
        myplot.plot_well(zonelogname="Zonelog")

        if show_plot:
            myplot.show()
        if generate_plot:
            myplot.savefig(join(tmpdir, "xsect_gbf1.png"), last=True)
        else:
            myplot.close()

    def test_line_segments_colors_maps_logs_and_missing_values(self) -> None:
        """Map log values to colors and use the fill color for missing entries."""
        dataframe = pd.DataFrame(
            {
                "R_HLEN": [0.0, 1.0, 2.0, 3.0],
                "Z_TVDSS": [10.0, 11.0, 12.0, 13.0],
                "ZONE": [1, 1, 2, 99],
            }
        )
        palette = [(1.0, 0.0, 0.0, 1.0), (0.0, 0.0, 1.0, 1.0)]
        fill_color = (0.0, 0.0, 0.0, 0.0)

        segments, colors = XSection._line_segments_colors(
            dataframe, {1: 0, 2: 1}, palette, "ZONE", fill_color
        )

        assert len(segments) == 3
        np.testing.assert_equal(
            colors, [list(palette[0]), list(palette[1]), list(fill_color)]
        )
        assert segments[0] == [(0.0, 10.0), (1.0, 11.0)]

    @pytest.mark.parametrize(
        ("method_name", "log_name"),
        [
            ("_plot_well_zlog", "ZONE"),
            ("_plot_well_faclog", "FACIES"),
            ("_plot_well_perflog", "PERF"),
        ],
    )
    def test_well_log_methods_add_line_collections(
        self, method_name: str, log_name: str
    ) -> None:
        """Render segments for each supported categorical well log."""
        myplot = XSection()
        dataframe = pd.DataFrame(
            {
                "R_HLEN": [0.0, 1.0, 2.0],
                "Z_TVDSS": [10.0, 11.0, 12.0],
                log_name: [1, 1, 2],
            }
        )
        figure, axes = plt.subplots()

        try:
            getattr(myplot, method_name)(
                dataframe, axes, (1.0, 1.0), log_name, legend=False
            )

            assert len(axes.collections) == 1
            assert isinstance(axes.collections[0], LineCollection)
        finally:
            plt.close(figure)

    def test_well_crossings_mark_closest_trajectory_point(self) -> None:
        """Mark the nearest trajectory point to each supplied crossing."""
        dataframe = pd.DataFrame(
            {
                "X_UTME": [0.0, 10.0],
                "Y_UTMN": [0.0, 0.0],
                "R_HLEN": [0.0, 10.0],
            }
        )
        crossings = pd.DataFrame(
            {
                "X_UTME": [8.0],
                "Y_UTMN": [1.0],
                "Z_TVDSS": [-100.0],
                "CWELL": ["crossing-well"],
            }
        )
        figure, axes = plt.subplots()

        try:
            XSection._plot_well_crossings(
                dataframe, axes, crossings, names=False, years=False
            )

            assert axes.collections
            assert len(axes.collections) == 2
            first_scatter = axes.collections[0].get_offsets()
            np.testing.assert_equal(first_scatter, [[10.0, -100.0]])
            assert not axes.texts
        finally:
            plt.close(figure)

    def test_set_xaxis_md_offsets_ticks_and_adds_gridlines(self) -> None:
        """Convert horizontal ticks to measured depth and add requested grids."""
        myplot = XSection()
        figure, axes = plt.subplots()
        axes.set_xticks([0.0, 50.0, 100.0])
        axes.set_xlim(0.0, 100.0)
        myplot._ax1 = {"main": axes}
        myplot._well = SimpleNamespace(
            get_dataframe=lambda copy=False: pd.DataFrame({"MDEPTH": [1234.0]})
        )

        try:
            myplot.set_xaxis_md(gridlines=True)

            assert [tick.get_text() for tick in axes.get_xticklabels()] == [
                "1200",
                "1250",
                "1300",
            ]
            assert axes.get_xlabel() == "Measured Depth [m]"
            assert axes.get_ylabel() == "TVD MSL [m]"
        finally:
            plt.close(figure)

    def test_plot_surfaces_rejects_more_surfaces_than_colors(self) -> None:
        """Raise when the active colormap cannot color every surface."""
        myplot = XSection()
        myplot._fence = np.array([[0.0, 0.0], [1.0, 1.0]])
        figure, axes = plt.subplots()
        myplot._ax1 = {"main": axes}
        myplot._colormap.N = 1
        surfaces = [SimpleNamespace(name="one"), SimpleNamespace(name="two")]

        try:
            with pytest.raises(ValueError, match="Too few colors"):
                myplot.plot_surfaces(surfaces=surfaces)
        finally:
            plt.close(figure)

    def test_simple_plot_with_seismics(self, tmpdir, show_plot, generate_plot):
        """Test as simple XSECT plot with seismic backdrop."""

        mywell = xtgeo.well_from_file(USEFILE7)
        mycube = xtgeo.cube_from_file(USEFILE6)

        mysurfaces = []
        mysurf = xtgeo.surface_from_file(USEFILE2)

        for i in range(10):
            xsurf = mysurf.copy()
            xsurf.values = xsurf.values + i * 20
            xsurf.name = f"Surface_{i}"
            mysurfaces.append(xsurf)

        myplot = XSection(
            zmin=1000,
            zmax=1900,
            well=mywell,
            surfaces=mysurfaces,
            cube=mycube,
            sampling=10,
            nextend=2,
        )

        # set the color table, from file
        clist = [0, 1, 222, 3, 5, 7, 3, 12, 11, 10, 9, 8]
        cfil1 = "xtgeo"
        cfil2 = TPATH / "etc/colortables/colfacies.txt"

        assert 222 in clist
        assert "xtgeo" in cfil1
        assert "colfacies" in str(cfil2)

        myplot.colormap = cfil1

        myplot.canvas(title="Plot with seismics", subtitle="Some well")

        myplot.plot_cube()
        myplot.plot_surfaces(fill=False)

        myplot.plot_well()

        myplot.plot_map()

        if generate_plot:
            myplot.savefig(join(tmpdir, "xsect_wcube.png"), last=False)

        if show_plot:
            myplot.show()

        myplot.close()

    def test_multiple_subplots(self, tmpdir, show_plot, generate_plot):
        """Test as simple XSECT plot."""

        mywell = xtgeo.well_from_file(USEFILE4)
        mysurf = xtgeo.surface_from_file(USEFILE2)

        myplot = XSection(zmin=1500, zmax=1800, well=mywell, surfaces=[mysurf])

        for i in range(4):
            myplot.canvas(title=str(i), subtitle="My Dear Well")

        myplot.close()

    def test_reek1(self, tmpdir, generate_plot):
        """Test XSect for a Reek well."""

        myfield = xtgeo.polygons_from_file(USEFILE3, fformat="xyz")

        mywells = []
        wnames = glob.glob(str(USEFILE4))
        wnames.sort()
        for wname in wnames:
            mywell = xtgeo.well_from_file(wname)
            mywells.append(mywell)

        mysurfaces = []
        surfnames = glob.glob(str(USEFILE5))
        surfnames.sort()
        for fname in surfnames:
            mysurf = xtgeo.surface_from_file(fname)
            mysurfaces.append(mysurf)

        # Troll lobes
        mylobes = []
        surfnames = glob.glob(str(USEFILE5))
        surfnames.sort()
        for fname in surfnames:
            mysurf = xtgeo.surface_from_file(fname)
            mylobes.append(mysurf)

        for wo in mywells:
            myplot = XSection(
                zmin=1500,
                zmax=1700,
                well=wo,
                surfaces=mysurfaces,
                zonelogshift=-1,
                outline=myfield,
            )

            myplot.canvas(
                title=wo.truewellname,
                subtitle="Before my corrections",
                infotext="Heisan sveisan",
                figscaling=1.2,
            )

            # myplot.colortable('xtgeo')

            myplot.plot_surfaces(fill=True)

            myplot.plot_surfaces(
                surfaces=mylobes,
                fill=False,
                linewidth=4,
                legendtitle="Lobes",
                fancyline=True,
            )

            myplot.plot_well(zonelogname="Zonelog")

            myplot.plot_wellmap()

            myplot.plot_map()

            if generate_plot:
                myplot.savefig(join(tmpdir, "xsect2a.svg"), fformat="svg", last=False)
                myplot.savefig(join(tmpdir, "xsect2a.png"), fformat="png")
            else:
                myplot.close()
