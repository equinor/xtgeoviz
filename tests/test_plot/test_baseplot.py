"""Test the baseplot module and class."""
import matplotlib
import pytest
from matplotlib.testing.decorators import image_comparison

from xtgeoviz.plot.baseplot import BasePlot


@pytest.mark.skip(reason="Graphical compare testing immature")
@image_comparison(baseline_images=["canvas"], remove_text=False, extensions=["png"])
def test_canvas():
    """Test the canvas function."""

    myplot = BasePlot()
    myplot.canvas(title="Hello canvas", subtitle="Hello Subtitle", infotext="Some info")


def test_colormap():
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
    assert myplot.get_colormap_as_table()[8] == pytest.approx((0.8, 0.196, 0.6, 1.0))
    assert xtgeomap.name == "xtgeo"
