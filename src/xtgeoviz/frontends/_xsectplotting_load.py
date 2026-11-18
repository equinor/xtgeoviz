"""Various helper functions for xsectplotting."""

from __future__ import annotations

import logging
import pathlib
from typing import TYPE_CHECKING

import xtgeo

if TYPE_CHECKING:
    # xsectplotting imports this module, so the owner type must stay type-only.
    from .xsectplotting import _Xsections

logger: logging.Logger = logging.getLogger(__name__)


def load_wells(x_sections: _Xsections) -> None:
    """Load wells and associated log settings into the application state.

    Uses preloaded objects when supplied; otherwise reads matching files from
    the configured well folder.

    Args:
        x_sections: Cross-section application receiving the loaded wells and logs.

    Raises:
        SystemExit: If no preloaded wells or matching files are available.
    """
    wlist = []

    if x_sections.config["input"]["wells"]["objects"]:
        wlist = x_sections.config["input"]["wells"]["objects"]

    else:
        wellfolder = pathlib.Path(x_sections.config["input"]["wells"]["folder"])
        wcard = x_sections.config["input"]["wells"]["wildcard"]

        for well in sorted(wellfolder.glob(wcard)):
            logger.info("Read well file: %s", well)
            wobj = xtgeo.well_from_file(
                well,
                zonelogname=x_sections.config["input"]["wells"]["zonelog"],
                strict=False,
            )
            wlist.append(wobj)

        if not wlist:
            raise SystemExit("Cannot plot, no wells as input")

    x_sections.wells["wlist"] = wlist

    x_sections.wells["zonelog"] = x_sections.config["input"]["wells"]["zonelog"]

    x_sections.wells["facieslog"] = None
    if x_sections.config["input"]["wells"]["facieslog"]:
        x_sections.wells["facieslog"] = x_sections.config["input"]["wells"]["facieslog"]

    x_sections.wells["perflog"] = None
    if x_sections.config["input"]["wells"]["perflog"]:
        x_sections.wells["perflog"] = x_sections.config["input"]["wells"]["perflog"]


def _load_surfaces_generic(x_sections: _Xsections, case: str = "primary") -> None:
    """Load and name one configured set of XTGeo regular surfaces.

    Preloaded objects take precedence over file paths. Loaded surfaces are
    stored in ``x_sections.surfaces[case]``.

    Args:
        x_sections: Cross-section application receiving the surfaces.
        case: Surface-set key to load, such as ``primary``, ``secondary``, or
            ``contacts``.

    Raises:
        RuntimeError: If a preloaded object is not an XTGeo regular surface.
    """
    config = x_sections.config
    sdict = []
    names = config["input"]["surfaces"][case]["names"]

    if config["input"]["surfaces"][case]["objects"]:
        sdict = config["input"]["surfaces"][case]["objects"]

    else:
        surffolder = None
        wcard = None
        if "folder" in config["input"]["surfaces"][case]:
            actualfolder = config["input"]["surfaces"][case]["folder"]
            if actualfolder:
                surffolder = pathlib.Path(actualfolder)
        if "wildcard" in config["input"]["surfaces"][case]:
            wcard = config["input"]["surfaces"][case]["wildcard"]
            if not wcard:
                wcard = ""

        sobjects = []
        if surffolder and wcard:
            for inum, surf in enumerate(sorted(surffolder.glob(wcard))):
                logger.info("Read surface file: %s", surf)
                sobjects.append(xtgeo.surface_from_file(surf))

        sdict = sobjects

    for inum, srf in enumerate(sdict):
        if not isinstance(srf, xtgeo.RegularSurface):
            raise RuntimeError("Surface object are not XTGeo objects")
        if names:
            srf.name = names[inum]
        else:
            srf.name = "Surface_" + str(inum)

    x_sections.surfaces[case] = sdict


def load_surfaces(x_sections: _Xsections) -> None:
    """Load the primary, secondary, and contact surface sets.

    Args:
        x_sections: Cross-section application receiving the loaded surfaces.
    """
    for casename in ["primary", "secondary", "contacts"]:
        _load_surfaces_generic(x_sections, case=casename)


def load_outline(x_sections: _Xsections) -> None:
    """Load the field outline from a path or use a supplied polygons object.

    Args:
        x_sections: Cross-section application receiving the outline.
    """

    outline = x_sections.config["input"]["outline"]

    if isinstance(outline, str):
        logger.info("Read outline: %s", outline)
        x_sections.outline = xtgeo.polygons_from_file(outline)
    elif isinstance(outline, xtgeo.Polygons):
        x_sections.outline = outline


def load_cube(x_sections: _Xsections) -> None:
    """Load the backdrop cube or use a supplied XTGeo cube object.

    Sets ``x_sections.cube`` to ``None`` when no cube is configured.

    Args:
        x_sections: Cross-section application receiving the cube.
    """

    cube = x_sections.config["input"]["cube"]

    if cube and isinstance(cube, str):
        logger.info("Reading cube: %s", cube)
        x_sections.cube = xtgeo.cube_from_file(cube)
        logger.info("Reading cube done")
    elif cube and isinstance(cube, xtgeo.Cube):
        x_sections.cube = cube
        logger.info("Apply an existing Cube instance: %s", type(cube))
    else:
        x_sections.cube = None


def load_grid(x_sections: _Xsections) -> None:
    """Load configured grid geometry and its property.

    Reads the geometry only when it is not already supplied through a surface
    source, and reads the property when both geometry and property paths are
    configured.

    Args:
        x_sections: Cross-section application receiving the grid and property.
    """

    gfile = x_sections.config["input"]["grid"]["geometry"]
    pfile = x_sections.config["input"]["grid"]["property"]["file"]
    pname = x_sections.config["input"]["grid"]["property"]["name"]
    pdate = x_sections.config["input"]["grid"]["property"]["date"]

    read_grid = True
    if gfile == x_sections.config["input"]["surfaces"]["fromgrid"]:
        # skip reading grid once more
        read_grid = False

    if gfile and pfile:
        if read_grid:
            logger.info("Reading grid geometry: %s", gfile)
            x_sections.grid = xtgeo.grid_from_file(gfile)
            logger.info("Reading grid geometry done")
        logger.info("Reading grid property: %s", pfile)
        x_sections.gridproperty = xtgeo.gridproperty_from_file(
            pfile, name=pname, date=pdate
        )
        logger.info("Reading grid property done")
