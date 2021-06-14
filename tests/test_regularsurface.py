import matplotlib.pyplot as plt
from matplotlib.testing.compare import compare_images
import numpy as np
import xtgeo
from xtgeoviz.mpl.quickplot import quickplot


def test_very_basic_to_file(tmp_path):
    """Just test that matplotlib works, to a file."""
    plt.title("Hello world")
    plt.savefig(tmp_path / "verysimple.png")

    assert (tmp_path / "verysimple.png").is_file() is True


def test_quickplot(tmp_path):
    """Test quickplot of a regular surface."""

    surf = xtgeo.RegularSurface(
        ncol=40, nrow=30, xinc=25, yinc=35, values=np.arange(40 * 30)
    )

    quickplot(surf, filename=tmp_path / "quickplot1.png")

    expected = "tests/baseline_images/test_regularsurface/quickplot1.png"
    actual = tmp_path / "quickplot1.png"

    assert compare_images(expected, actual, 0.01) is None
