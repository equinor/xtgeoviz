"""Test the baseplot module and class."""

import pathlib

import matplotlib
import pytest
from matplotlib.testing.decorators import image_comparison

from xtgeoviz.plot.baseplot import BasePlot


class TestBasePlot:
    """Tests for the shared plotting base class."""

    @pytest.mark.skip(reason="Graphical compare testing immature")
    @image_comparison(baseline_images=["canvas"], remove_text=False, extensions=["png"])
    def test_canvas(self):
        """Test the canvas function."""

        myplot = BasePlot()
        myplot.canvas(
            title="Hello canvas", subtitle="Hello Subtitle", infotext="Some info"
        )

    def test_colormap(self):
        """Test colormap functions."""

        myplot = BasePlot()

        cmap = myplot.colormap
        colors = myplot.get_colormap_as_table()

        assert colors[1] == pytest.approx((0.26851, 0.009605, 0.335427, 1.0))
        assert cmap.name == "viridis"
        assert isinstance(cmap, matplotlib.colors.LinearSegmentedColormap)

        xtgeomap = myplot.define_any_colormap("xtgeo")
        myplot.colormap = xtgeomap
        assert isinstance(xtgeomap, matplotlib.colors.LinearSegmentedColormap)
        assert myplot.get_colormap_as_table()[1] == pytest.approx((0.0, 0.0, 0.0, 1))
        assert myplot.get_colormap_as_table()[8] == pytest.approx(
            (0.8, 0.196, 0.6, 1.0)
        )
        assert xtgeomap.name == "xtgeo"

    @pytest.mark.parametrize(
        "name, expected_size", [("random40", 40), ("randomc", 256)]
    )
    def test_named_random_colormaps(self, name: str, expected_size: int) -> None:
        """Build named random palettes with their expected entry counts."""
        cmap = BasePlot.define_any_colormap(name)

        assert cmap.name == name
        assert expected_size == cmap.N

    def test_unknown_colormap_warns_and_falls_back_to_rainbow(self) -> None:
        """Warn and use rainbow when the requested colormap is unavailable."""
        with pytest.warns(UserWarning, match="not installed"):
            cmap = BasePlot.define_any_colormap("not-a-registered-colormap")

        assert cmap.name == "rainbow"

    def test_rms_colormap_reads_file_colors(self, tmp_path: pathlib.Path) -> None:
        """Create an RMS colormap using the RGB entries in a file."""
        palette_file = tmp_path / "palette.rms"
        palette_file.write_text(
            "ColorMap.color(0) = 0.1 0.2 0.3\nColorMap.color(1) = 0.7 0.8 0.9\n",
            encoding="utf-8",
        )

        cmap = BasePlot.define_any_colormap(str(palette_file))

        assert cmap.name == str(palette_file)
        assert cmap.N == 2
        assert cmap(0.0) == pytest.approx((0.1, 0.2, 0.3, 1.0))

    def test_colormap_colorlist_selects_and_reorders_colors(self):
        """Use colorlist indices to select and order the resulting palette."""
        base_cmap = BasePlot.define_any_colormap("xtgeo")
        base_colors = [
            base_cmap(index / (base_cmap.N - 1)) for index in range(base_cmap.N)
        ]
        indices = [2, 0, 2]

        cmap = BasePlot.define_any_colormap("xtgeo", colorlist=indices)

        assert cmap.name == "user"
        assert len(indices) == cmap.N
        for position, color_index in enumerate(indices):
            assert cmap(position / 2) == pytest.approx(base_colors[color_index])

    def test_colorlist_uses_default_rainbow_palette(self):
        """Allow color selection when no colormap name is provided."""
        base_cmap = BasePlot.define_any_colormap("rainbow")
        indices = [5, 1]

        cmap = BasePlot.define_any_colormap(None, colorlist=indices)

        assert len(indices) == cmap.N
        for position, color_index in enumerate(indices):
            expected = base_cmap(color_index / (base_cmap.N - 1))
            assert cmap(position) == pytest.approx(expected)

    @pytest.mark.parametrize("color_index", [-1, 256])
    def test_colorlist_rejects_out_of_range_indices(self, color_index):
        """Reject negative and too-large palette indices."""
        with pytest.raises(ValueError, match="colorlist"):
            BasePlot.define_any_colormap("rainbow", colorlist=[color_index])
