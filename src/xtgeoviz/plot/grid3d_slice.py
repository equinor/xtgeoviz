"""Module for 3D Grid slice plots, using matplotlib."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon

from ._libwrapper import matplotlib_colormap
from .baseplot import BasePlot

if TYPE_CHECKING:
    import xtgeo
    from matplotlib.colors import Colormap

logger: logging.Logger = logging.getLogger(__name__)


class Grid3DSlice(BasePlot):
    """Class for plotting a row, a column, or a layer, using matplotlib."""

    def __init__(self) -> None:
        """Construct an instance for a Grid3DSlice object."""
        super().__init__()

        self._wells = None
        self._surface = None
        self._tight = False

        self._wfence = None
        self._legendtitle = "Map"

        self.define_colormap("rainbow")
        self._linecolor: str | tuple[float, ...] = "black"
        self._clist = None
        self._prop: Any = None
        self._grid: Any = None
        self._geomlist = None
        self._index = 1
        self._actnum = None
        self._window: tuple[float, float, float, float] | None = None
        self._active = True
        self._minvalue: float | None = None
        self._maxvalue: float | None = None

    def plot_gridslice(
        self,
        grid: xtgeo.Grid,
        prop: xtgeo.GridProperty | None = None,
        mode: str = "layer",
        minvalue: float | None = None,
        maxvalue: float | None = None,
        colormap: Colormap | str | None = None,
        linecolor: str | tuple[float, ...] = "black",
        index: int = 1,
        window: tuple[float, float, float, float] | None = None,
        activeonly: bool = True,
    ) -> None:
        """Plot a row slice, column slice or layer slice of a grid.

        Args:
            grid (Grid): The XTGeo grid object
            prop (GridProperty, optional): The XTGeo grid property object
            mode (str): Choose between 'column', 'row', 'layer' (default)
            minvalue (float): Minimum level color scale (default: from data)
            maxvalue (float): Maximum level color scale (default: from data)
            index (int): Index to plot e.g layer number if layer slice (first=1)
            colormap: Color map to use for cells, e.g. 'rainbow' or an rmscol file
            linecolor (str or tuple): Color of grid lines (black/white/grey
                or a tuple with 4 numbers on valid matplotlib format)
            activeonly (bool): If only use active cells
            window (str): Some window

        """
        self._index = index
        if isinstance(colormap, str):
            try:
                self.colormap = matplotlib_colormap(colormap)
            except (KeyError, ValueError):
                self.define_colormap(colormap)
        elif colormap is not None:
            self._colormap = colormap

        self._linecolor = linecolor
        if not isinstance(linecolor, tuple) and linecolor not in (
            "black",
            "grey",
            "white",
        ):
            raise ValueError("Value of linecolor is invalid")

        self._clist = grid.get_xyz_corners()  # get XYZ for each corner, 24 arrays
        self._grid = grid
        self._prop = prop
        self._window = window

        if self._geomlist is None:
            # returns (xori, yori, zori, xmin, xmax, ymin, ymax, zmin, zmax,...)
            self._geomlist = grid.get_geometrics(allcells=True, cellcenter=False)

        self._active = activeonly

        self._minvalue = minvalue
        self._maxvalue = maxvalue

        if mode in ("column", "row"):
            pass  # self._plot_row()
        else:
            self._plot_layer()

    def _plot_layer(self) -> None:
        """Render the selected grid layer as polygon patches."""
        xyc, ibn = self._grid.get_layer_slice(self._index, activeonly=self._active)

        xval = xyc[:, :, 0]
        yval = xyc[:, :, 1]

        xvmin = xval.min()
        xvmax = xval.max()
        yvmin = yval.min()
        yvmax = yval.max()

        if self._window is None:
            xmin = xvmin - 0.05 * (abs(xvmax - xvmin))
            xmax = xvmax + 0.05 * (abs(xvmax - xvmin))
            ymin = yvmin - 0.05 * (abs(yvmax - yvmin))
            ymax = yvmax + 0.05 * (abs(yvmax - yvmin))
        else:
            xmin, xmax, ymin, ymax = self._window

        patches = []

        for pos in range(len(ibn)):
            nppol = xyc[pos, :, :]
            if nppol.mean() > 0.0:
                polygon = Polygon(nppol)
                patches.append(polygon)

        patchcoll = PatchCollection(
            patches, edgecolors=(self._linecolor,), cmap=self.colormap
        )

        if self._prop:
            pvalues = self._prop.values
            pvalues = pvalues[:, :, self._index - 1]
            pvalues = pvalues[~pvalues.mask]

            patchcoll.set_array(pvalues)

            pmin = self._minvalue
            if self._minvalue is None:
                pmin = pvalues.min()

            pmax = self._maxvalue
            if self._maxvalue is None:
                pmax = pvalues.max()

            patchcoll.set_clim(pmin, pmax)

        im = self._ax.add_collection(patchcoll)
        self._ax.set_xlim((xmin, xmax))
        self._ax.set_ylim((ymin, ymax))
        self._fig.colorbar(im)

        plt.gca().set_aspect("equal", adjustable="box")
