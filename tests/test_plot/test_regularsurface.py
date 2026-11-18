import pathlib
from unittest.mock import MagicMock

import matplotlib.pyplot as plt
import matplotlib.testing as mtst
import numpy as np
import pytest
import xtgeo
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.testing.compare import compare_images

import xtgeoviz.plot.quickplot as quickplot_module
from xtgeoviz.plot import Map
from xtgeoviz.plot.quickplot import quickplot


class TestRegularSurface:
    """Tests for regular-surface plotting."""

    def test_very_basic_to_file(self, tmp_path: pathlib.Path) -> None:
        """Just test that matplotlib works, to a file."""
        plt.title("Hello world")
        plt.savefig(tmp_path / "verysimple.png")

        assert (tmp_path / "verysimple.png").is_file() is True

    def test_quickplot(self, tmp_path: pathlib.Path) -> None:
        """Test quickplot of a regular surface."""

        surf = xtgeo.RegularSurface(
            ncol=40, nrow=30, xinc=25, yinc=35, values=np.arange(40 * 30)
        )

        mtst.set_font_settings_for_testing()
        mtst.set_reproducibility_for_testing()
        mtst.set_reproducibility_for_testing()

        quickplot(surf, filename=tmp_path / "quickplot1.png")

        expected = "tests/baseline_images/test_regularsurface/quickplot1.png"
        actual = str(tmp_path / "quickplot1.png")

        assert compare_images(expected, actual, 50.0) is None

    def test_quickplot_accepts_matplotlib_colormap_object(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """Pass Matplotlib colormap objects through to the map plot."""
        surface = xtgeo.RegularSurface(
            ncol=3, nrow=2, xinc=1, yinc=1, values=np.arange(6, dtype=float)
        )
        colormap = LinearSegmentedColormap.from_list("custom", ["red", "blue"])
        mymap = Map()
        plot_surface = MagicMock()
        monkeypatch.setattr(quickplot_module, "Map", lambda: mymap)
        monkeypatch.setattr(mymap, "canvas", MagicMock())
        monkeypatch.setattr(mymap, "plot_surface", plot_surface)
        monkeypatch.setattr(mymap, "savefig", MagicMock())

        quickplot_module.quickplot_regularsurface(
            surface,
            filename=tmp_path / "quickplot.png",
            colormap=colormap,
        )

        assert mymap.colormap is colormap
        plot_surface.assert_called_once()
