"""Module for quickplot of different xtgeo data types.

Typically::

    import xtgeo
    from xtgeoviz import quickplot

    surf = xtgeo.surface_from_file("some.gri")

    quickplot(surf)

"""
import warnings
import pathlib
from typing import Optional, Union
import xtgeo
import xtgeoviz


def quickplot(xobj, **kwargs):
    """A common entry point for quickplot."""
    if isinstance(xobj, xtgeo.RegularSurface):
        quickplot_regularsurface(xobj, **kwargs)

    # elif isinstance(xobj, xtgeo.Grid):
    #     quickplot_gridproperty(xobj, **kwargs)


def quickplot_regularsurface(
    regsurf: xtgeo.RegularSurface,
    filename: Optional[Union[str, pathlib.Path]] = None,
    title: Optional[str] = "QuickPlot for Surface",
    subtitle: Optional[str] = None,
    infotext: Optional[str] = None,
    minmax: Optional[tuple] = (None, None),
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


# def quickplot_gridproperty(
#     grid,
#     filename,
#     propertyname: Optional[str] = None,
#     title: Optional[str] = "QuickPlot for Surfaces",
#     subtitle: Optional[str] = None,
#     infotext: Optional[str] = None,
#     minmax: Optional[tuple] = (None, None),
#     xlabelrotation: Optional[float] = None,
#     colormap: Optional[str] = "rainbow",
#     faults: Optional[xtgeo.Polygons] = None,
#     logarithmic: Optional[bool] = False,
# ):
#     """Quickplot grid with assosiated grid properties."""

#     mymap = xtgeoviz.mpl.grid3d_slice.Grid3DSlice()

#     mymap.canvas(title=title, subtitle=subtitle, infotext=infotext)

#     if filename is None:
#         mymap.show()
#     else:
#         mymap.savefig(filename)
