"""Compatibility wrapper when major libs changes API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

import matplotlib
import scipy

if TYPE_CHECKING:
    import numpy as np
    from matplotlib.axes import Axes
    from matplotlib.colors import Colormap
    from numpy.typing import NDArray


def _version_ge_than(proposed: str, comparewith: str) -> bool:
    """Simple version checker, assuming version on form x.y.z

    Returns True of proposed is >= comparewith
    """

    xvx = proposed.split(".")
    yvx = comparewith.split(".")

    xversion = float(f"{xvx[0]}.{int(xvx[1]):03d}{int(xvx[2]):03d}")
    yversion = float(f"{yvx[0]}.{int(yvx[1]):03d}{int(yvx[2]):03d}")

    return xversion >= yversion


def matplotlib_colormap(name: str) -> Colormap:
    """Compatibility wrapper for matplotlib colormaps syntax that change across 3.6."""
    return (
        matplotlib.colormaps[name]
        if _version_ge_than(matplotlib.__version__, "3.6.0")
        else matplotlib.pyplot.cm.get_cmap(name)  # type: ignore[attr-defined]
    )


def matplotlib_set_xticks(
    axes: Axes, ticks: Sequence[float], labels: Sequence[str]
) -> None:
    """Set tick locations and labels using the supported Matplotlib API.

    Args:
        axes: Matplotlib axes receiving the tick locations and labels.
        ticks: Tick locations to set.
        labels: Labels corresponding to the tick locations.
    """
    if _version_ge_than(matplotlib.__version__, "3.5.0"):
        axes.set_xticks(ticks, labels=labels)
    else:
        axes.set_xticks(ticks)
        axes.set_xticklabels(labels)


def scipy_gaussianfilter(
    inputv: NDArray[np.generic], sigma: float | Sequence[float]
) -> NDArray[np.generic]:
    """Compatibility wrapper for scipy gaussian_filter syntax that change across 1.8."""
    return (
        scipy.ndimage.gaussian_filter(inputv, sigma)
        if _version_ge_than(scipy.__version__, "1.8.0")
        else scipy.ndimage.filters.gaussian_filter(inputv, sigma)
    )
