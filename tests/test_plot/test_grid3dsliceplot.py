import os
import pathlib
from typing import Any
from unittest.mock import MagicMock

import pytest
import xtgeo

from xtgeoviz.plot import Grid3DSlice

TPATH = pathlib.Path("../xtgeo-testdata")

USEFILE1 = TPATH / "3dgrids/reek/reek_sim_grid.roff"
USEFILE2 = TPATH / "3dgrids/reek/reek_sim_poro.roff"
USEFILE3 = TPATH / "etc/colortables/rainbow_reverse.rmscolor"


class TestGrid3DSlice:
    """Tests for three-dimensional grid slice plotting."""

    @pytest.mark.parametrize(
        ("colormap", "expected_name"),
        [("viridis", "viridis"), ("rainbow_r", "rainbow_r"), ("xtgeo", "xtgeo")],
    )
    def test_plot_gridslice_resolves_colormap_strings(
        self, colormap: str, expected_name: str
    ) -> None:
        """Resolve registered Matplotlib names and retain XTGeo aliases."""
        plot = Grid3DSlice()

        plot.plot_gridslice(MagicMock(), mode="row", colormap=colormap)

        assert plot.colormap.name == expected_name

    def test_slice_simple_layer(
        self, tmpdir: Any, show_plot: bool, generate_plot: bool
    ) -> None:
        """Trigger XSection class, and do some simple things basically."""
        layslice = Grid3DSlice()

        mygrid = xtgeo.grid_from_file(USEFILE1)
        myprop = xtgeo.gridproperty_from_file(USEFILE2, grid=mygrid, name="PORO")

        assert myprop.values.mean() == pytest.approx(0.1677, abs=0.001)

        wd = None  # [457000, 464000, 1650, 1800]
        for lay in range(1, mygrid.nlay + 1):
            layslice.canvas(title=f"My Grid Layer plot for layer {lay}")
            layslice.plot_gridslice(
                mygrid,
                prop=myprop,
                mode="layer",
                index=lay,
                window=wd,
                linecolor="black",
            )

            if show_plot:
                layslice.show()
            if generate_plot:
                layslice.savefig(
                    os.path.join(tmpdir, "layerslice_" + str(lay) + ".png")
                )
            layslice.close()
