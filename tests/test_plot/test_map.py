import pathlib
from os.path import join
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
import xtgeo
from matplotlib.colors import Colormap, LinearSegmentedColormap, ListedColormap
from matplotlib.patches import Polygon

from xtgeoviz.plot import Map

TPATH = pathlib.Path("../xtgeo-testdata")

SFILE1 = TPATH / "surfaces/reek/1/topreek_rota.gri"
PFILE1 = TPATH / "polygons/reek/1/top_upper_reek_faultpoly.pol"
SFILE2 = TPATH / "surfaces/reek/1/reek_perm_lay1.gri"


class TestMap:
    """Tests for map plotting."""

    def test_simple_plot(self, tmpdir: Any, generate_plot: bool) -> None:
        """Test as simple map plot only making an instance++ and plot."""

        mysurf = xtgeo.surface_from_file(SFILE1)

        # just make the instance, with a lot of defaults behind the scene
        myplot = Map()
        myplot.canvas(title="My o my")
        myplot.colormap = "gist_ncar"  # type: ignore[assignment]
        myplot.plot_surface(mysurf)

        if generate_plot:
            myplot.savefig(join(tmpdir, "map_simple.png"), last=True)
        else:
            myplot.close()

    def test_map_plot_with_points(self, tmpdir: Any, generate_plot: bool) -> None:
        """Test as simple map plot with underlying points."""

        mysurf = xtgeo.surface_from_file(SFILE1)

        mypoints = xtgeo.points_from_surface(mysurf)

        df = mypoints.get_dataframe()
        mypoints.set_dataframe(df[::20])

        # just make the instance, with a lot of defaults behind the scene
        myplot = Map()
        myplot.canvas(title="My o my")
        myplot.colormap = "gist_ncar"  # type: ignore[assignment]
        myplot.plot_surface(mysurf)
        myplot.plot_points(mypoints)

        if generate_plot:
            myplot.savefig(join(tmpdir, "map_with_points.png"), last=True)
        else:
            myplot.close()

    def test_more_features_plot(self, tmpdir: Any, generate_plot: bool) -> None:
        """Map with some more features added, such as label rotation."""

        mysurf = xtgeo.surface_from_file(SFILE1)

        myfaults = xtgeo.polygons_from_file(PFILE1)

        # just make the instance, with a lot of defaults behind the scene
        myplot = Map()
        myplot.canvas(title="Label rotation")
        myplot.colormap = "rainbow"  # type: ignore[assignment]
        myplot.plot_surface(mysurf, minvalue=1250, maxvalue=2200, xlabelrotation=45)

        myplot.plot_faults(myfaults)

        if generate_plot:
            myplot.savefig(join(tmpdir, "map_more1.png"), last=True)
        else:
            myplot.close()

    def test_perm_logarithmic_map(self, tmpdir: Any, generate_plot: bool) -> None:
        """Map with PERM, log scale."""

        mysurf = xtgeo.surface_from_file(SFILE2)

        myplot = Map()
        myplot.canvas(title="PERMX normal scale")
        myplot.colormap = "rainbow"  # type: ignore[assignment]
        myplot.plot_surface(
            mysurf, minvalue=0, maxvalue=6000, xlabelrotation=45, logarithmic=True
        )

        if generate_plot:
            myplot.savefig(join(tmpdir, "permx_normal.png"), last=True)
        else:
            myplot.close()

    def test_constant_surface_uses_single_contour_level(self) -> None:
        """Plot a constant-valued surface through the single-level branch."""
        surface = xtgeo.RegularSurface(
            ncol=2, nrow=2, xinc=1, yinc=1, values=np.full(4, 5.0)
        )
        myplot = Map()
        myplot.canvas()
        original_colormap = myplot.colormap

        myplot.plot_surface(surface, colormap="rainbow")

        assert myplot.colormap is original_colormap
        myplot.close()

    def test_plot_surface_restores_colormap_after_contour_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Restore the instance colormap after Matplotlib rejects contours."""
        surface = xtgeo.RegularSurface(
            ncol=2, nrow=2, xinc=1, yinc=1, values=np.arange(4, dtype=float)
        )
        myplot = Map()
        myplot.canvas()
        original_colormap = myplot.colormap
        monkeypatch.setattr(
            myplot._ax,
            "contourf",
            lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("bad levels")),
        )

        myplot.plot_surface(surface, colormap="rainbow")

        assert myplot.colormap is original_colormap
        myplot.close()

    @pytest.mark.parametrize(
        "colormap",
        [
            LinearSegmentedColormap.from_list("linear", ["red", "blue"]),
            ListedColormap(["red", "blue"]),
        ],
    )
    def test_plot_surface_accepts_matplotlib_colormap_objects(
        self, monkeypatch: pytest.MonkeyPatch, colormap: Colormap
    ) -> None:
        """Use Matplotlib colormap objects without routing them through aliases."""
        surface = xtgeo.RegularSurface(
            ncol=2, nrow=2, xinc=1, yinc=1, values=np.arange(4, dtype=float)
        )
        if isinstance(colormap, ListedColormap):
            colormap.set_under("green")
            colormap.set_over("yellow")
            colormap.set_bad("black")

        myplot = Map()
        myplot.canvas()
        contourf = MagicMock(return_value=MagicMock())
        monkeypatch.setattr(myplot._ax, "contourf", contourf)
        monkeypatch.setattr(myplot._fig, "colorbar", MagicMock())

        try:
            myplot.plot_surface(surface, colormap=colormap)

            used_colormap = contourf.call_args.kwargs["cmap"]
            assert used_colormap is colormap
            assert used_colormap.name == colormap.name
            assert used_colormap(0.0) == pytest.approx(colormap(0.0))
            assert used_colormap(1.0) == pytest.approx(colormap(1.0))
            np.testing.assert_array_equal(
                used_colormap.get_under(), colormap.get_under()
            )
            np.testing.assert_array_equal(used_colormap.get_over(), colormap.get_over())
            np.testing.assert_array_equal(used_colormap.get_bad(), colormap.get_bad())
        finally:
            myplot.close()

    def test_plot_faults_draws_closed_polygons(self) -> None:
        """Add a closed fault polygon to the map axes."""
        fault_polygons = SimpleNamespace(
            get_dataframe=lambda copy=False: pd.DataFrame(
                {
                    "POLY_ID": [1, 1, 1, 1],
                    "X_UTME": [0.0, 1.0, 0.0, 0.0],
                    "Y_UTMN": [0.0, 0.0, 1.0, 0.0],
                }
            )
        )
        myplot = Map()
        myplot.canvas()

        try:
            myplot.plot_faults(fault_polygons)

            assert any(
                isinstance(artist, Polygon) for artist in myplot._ax.get_children()
            )
        finally:
            myplot.close()

    def test_plot_faults_raises_for_open_polygons(self) -> None:
        """Raise when a fault polygon's coordinates are not closed."""
        fault_polygons = SimpleNamespace(
            get_dataframe=lambda copy=False: pd.DataFrame(
                {
                    "POLY_ID": [1, 1, 1],
                    "X_UTME": [0.0, 1.0, 0.0],
                    "Y_UTMN": [0.0, 0.0, 1.0],
                }
            )
        )
        myplot = Map()
        myplot.canvas()

        try:
            with pytest.raises(OSError, match="A polygon is not closed"):
                myplot.plot_faults(fault_polygons)

            assert not any(
                isinstance(artist, Polygon) for artist in myplot._ax.get_children()
            )
        finally:
            myplot.close()
