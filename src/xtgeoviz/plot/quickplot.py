"""Module for quickplot of different xtgeo data types.

Typically::

    import xtgeo
    from xtgeoviz import quickplot

    surf = xtgeo.surface_from_file("some.gri")

    quickplot(surf)

"""
from __future__ import annotations

import pathlib
import warnings
from typing import Optional, Union

import xtgeo

from .xtmap import Map


def quickplot(xobj, **kwargs):
    """A common entry point for quickplot."""
    if isinstance(xobj, xtgeo.RegularSurface):
        quickplot_regularsurface(xobj, **kwargs)


def quickplot_regularsurface(
    regsurf: xtgeo.RegularSurface,
    filename: Optional[Union[str, pathlib.Path]] = None,
    title: Optional[str] = "QuickPlot for Surface",
    subtitle: Optional[str] = None,
    infotext: Optional[str] = None,
    minmax: tuple[int | float | None, int | float | None] = (None, None),
    xlabelrotation: Optional[float] = None,
    colormap: Optional[str] = "rainbow",
    faults: Optional[xtgeo.Polygons] = None,
    logarithmic: Optional[bool] = False,
):
    """Quickplot regularsurface."""

    ncount = regsurf.values.count()
    if ncount < 5:
        warnings.warn(
            f"None or too few map nodes for plotting. Skip output {filename}!",
            UserWarning,
        )
        return

    mymap = Map()
    mymap.canvas(title=title, subtitle=subtitle, infotext=infotext)

    minvalue, maxvalue = minmax
    mymap.colormap = colormap

    mymap.plot_surface(
        regsurf,
        minvalue=minvalue,
        maxvalue=maxvalue,
        xlabelrotation=xlabelrotation,
        logarithmic=logarithmic,
    )
    if faults:
        mymap.plot_faults(faults["faults"])

    if filename is None:
        mymap.show()
    else:
        mymap.savefig(filename)
