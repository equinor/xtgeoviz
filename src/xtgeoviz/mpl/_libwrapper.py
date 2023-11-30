"""Compatibility wrapper when major libs changes API."""
from __future__ import annotations

import matplotlib
import scipy

# pylint: disable=no-member


def _version_ge_than(proposed, comparewith):
    """Simple version checker, assuming version on form x.y.z

    Returns True of proposed is >= comparewith
    """

    xvx = proposed.split(".")
    yvx = comparewith.split(".")

    xversion = float(f"{xvx[0]}.{int(xvx[1]):03d}{int(xvx[2]):03d}")
    yversion = float(f"{yvx[0]}.{int(yvx[1]):03d}{int(yvx[2]):03d}")

    return xversion >= yversion


def matplotlib_colormap(name):
    """Compatibility wrapper for matplotlib colormaps syntax that change across 3.6."""
    if _version_ge_than(matplotlib.__version__, "3.6.0"):
        return matplotlib.colormaps[name]
    else:
        return matplotlib.pyplot.cm.get_cmap(name)


def scipy_gaussianfilter(inputv, sigma):
    """Compatibility wrapper for scipy gaussian_filter syntax that change across 1.8."""
    if _version_ge_than(scipy.__version__, "1.8.0"):
        return scipy.ndimage.gaussian_filter(inputv, sigma)
    else:
        return scipy.ndimage.filters.gaussian_filter(inputv, sigma)
