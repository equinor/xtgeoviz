"""Various helper functions for xsectplotting."""
from __future__ import annotations

import logging
import pathlib

import xtgeo

logger = logging.getLogger(__name__)


def load_wells(self):
    """Load wells from files, return as XTGeo well objects."""
    wlist = []

    if self.config["input"]["wells"]["objects"]:
        wlist = self.config["input"]["wells"]["objects"]

    else:
        wellfolder = pathlib.Path(self.config["input"]["wells"]["folder"])
        wcard = self.config["input"]["wells"]["wildcard"]

        for well in sorted(wellfolder.glob(wcard)):
            logger.info("Read well file: %s", well)
            wobj = xtgeo.well_from_file(
                well,
                zonelogname=self.config["input"]["wells"]["zonelog"],
                strict=False,
            )
            wlist.append(wobj)

        if not wlist:
            raise SystemExit("Cannot plot, no wells as input")

    self.wells["wlist"] = wlist

    self.wells["zonelog"] = self.config["input"]["wells"]["zonelog"]

    self.wells["facieslog"] = None
    if self.config["input"]["wells"]["facieslog"]:
        self.wells["facieslog"] = self.config["input"]["wells"]["facieslog"]

    self.wells["perflog"] = None
    if self.config["input"]["wells"]["perflog"]:
        self.wells["perflog"] = self.config["input"]["wells"]["perflog"]


def _load_surfaces_generic(self, case="primary"):
    """Load surfaces from files or grid, return as XTGeo RegularSurface objects.
    Note that the return is a dictionary with several possible surface
    sets: 'primary', 'secondary', 'tertiary', 'contacts'
    ::
    sdict:
       primary:
         [surfaceinstance1, surfaceinstance2, ...]
       contacts:
         [surfacieinstancex, surfacieinstancey, ...]
    Note the surface.name attribute is used to store the display surface name.
    """
    config = self.config
    sdict = dict()
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

    self.surfaces[case] = sdict


def load_surfaces(self):
    for casename in ["primary", "secondary", "contacts"]:
        _load_surfaces_generic(self, case=casename)


def load_outline(self):
    """Load field outline from file, return as XTGeo Polygons objects."""

    outline = self.config["input"]["outline"]

    if isinstance(outline, str):
        logger.info("Read outline: %s", outline)
        self.outline = xtgeo.polygons_from_file(outline)
    elif isinstance(outline, xtgeo.Polygons):
        self.outline = outline


def load_cube(self):
    """Apply a current cube or load a cube, both as XTGeo Cube"""

    cube = self.config["input"]["cube"]

    if cube and isinstance(cube, str):
        logger.info("Reading cube: %s", cube)
        self.cube = xtgeo.cube_from_file(cube)
        logger.info("Reading cube done")
    elif cube and isinstance(cube, xtgeo.Cube):
        self.cube = cube
        logger.info("Apply an existing Cube instance: %s", type(cube))
    else:
        self.cube = None


def load_grid(self):
    """Load a grid with property"""

    gfile = self.config["input"]["grid"]["geometry"]
    pfile = self.config["input"]["grid"]["property"]["file"]
    pname = self.config["input"]["grid"]["property"]["name"]
    pdate = self.config["input"]["grid"]["property"]["date"]

    read_grid = True
    if gfile == self.config["input"]["surfaces"]["fromgrid"]:
        # skip reading grid once more
        read_grid = False

    if gfile and pfile:
        if read_grid:
            logger.info("Reading grid geometry: %s", gfile)
            self.grid = xtgeo.grid_from_file(gfile)
            logger.info("Reading grid geometry done")
        logger.info("Reading grid property: %s", pfile)
        self.gridproperty = xtgeo.gridproperty_from_file(pfile, name=pname, date=pdate)
        logger.info("Reading grid property done")
