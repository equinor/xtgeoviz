"""Module for quickplot of different xtgeo data types.

Typically::

    import xtgeo
    from xtgeoviz import quickplot

    surf = xtgeo.surface_from_file("some.gri")

    quickplot(surf)

"""
import warnings
from typing import Optional

import xtgeo
import xtgeoviz


# type: ignore
def quickplot(  # pylint: disable=unused-argument
    xobj: xtgeo.RegularSurface,
    filename: Optional[str] = None,
    title="QuickPlot for Surfaces",
    subtitle=None,
    infotext=None,
    minmax=(None, None),
    xlabelrotation=None,
    colormap="rainbow",
    colortable=None,
    faults=None,
    logarithmic=False,
):
    if isinstance(xobj, xtgeo.RegularSurface):
        _quickplot_regularsurface(
            xobj,
            filename,
            title,
            subtitle,
            infotext,
            minmax,
            xlabelrotation,
            colormap,
            faults,
            logarithmic,
        )


def _quickplot_regularsurface(
    regsurf,
    filename,
    title,
    subtitle,
    infotext,
    minmax,
    xlabelrotation,
    colormap,
    faults,
    logarithmic,
):
    """Quickplot regularsurface."""

    ncount = regsurf.values.count()
    if ncount < 5:
        warnings.warn(
            "None or too few map nodes for plotting. Skip "
            "output {}!".format(filename),
            UserWarning,
        )
        return

    mymap = xtgeoviz.mpl.xtmap.Map()

    mymap.canvas(title=title, subtitle=subtitle, infotext=infotext)

    minvalue = minmax[0]
    maxvalue = minmax[1]

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
