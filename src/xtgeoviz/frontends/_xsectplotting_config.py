"""Config option for xsections"""
from __future__ import annotations

import logging
import re
from copy import deepcopy
from typing import Optional, Union

import six
import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = """
title: UnknownField

verbosity: normal  # alt: silent, info, debug

input:

    # source of various xsections
    wells:
        objects: No  # xtgeo Wells() object, alternative to folder/wildcard
        folder: No
        wildcard: "*"
        zonelog: ZONELOG
        perflog: No
        facieslog: No

    # data to show along xsections
    surfaces:
        primary:
            objects: No
            folder: No
            names: []
            wildcard: "*"

        secondary:
            objects: No
            folder: No
            names: []
            wildcard: "*"

        contacts:
            objects: No
            folder: No
            names: []
            wildcard: "*"

    outline: No

    cube: No

    grid:
        surfaces: No
        geometry: No
        property:
            file: No
            name: No
            date: No


plotsettings:

    general:
        engine: matplotlib  # Alternatives not implemented yet

    design:
        style: 1
        zrange: smart1
        gridlines: both
        subtitle: ""
        legendsize: 6
        legends: True
        dpi: 100

    wellmap:
        otherwells: No
        expand: 2

    surfaces:
        primary:
            colors: random40
            fill: Yes

        secondary:
            colors: xtgeo
            legend: Secondary

        contacts:
            colors: rainbow

    cube:
        colors: seismic
        range: []
        interpolation: gaussian
        alpha: 0.8
        sampling: nearest

    grid:
        colors: rainbow
        range: []
        alpha: 0.8
        zinc: 0.5

    wells:
        zonelog:
            colors: random40
            zoneshift: 0
            colordict: {}

        facieslog:
            colors: xtgeo
            colordict: {}

        perflog:
            colors: xtgeo
            colordict: {}

        wellcrossings:
            show: No
            sampling: 20
            wfilter: 5

output:
    plotfolder: /tmp
    format: svg
    prefix: No
    pdfjoin: No
    cleanup: No
"""


class ConfigError(Exception):
    """Exception for config reading error."""

    ...


def config_defaults(as_yaml: Optional[bool] = True) -> Union[str, dict]:
    """The YAML file full spec with defaults!

    Args:
        as_yaml: If True, then return as string on YAML format, else, return a
            python dict.
    """
    logger.info("Configure default settings with as_yaml set to: %s", as_yaml)
    if as_yaml:
        return DEFAULT_CONFIG

    return yaml.safe_load(DEFAULT_CONFIG)


def _invalid_key(superset, subset):
    """Simple test if keyword in subset is present in superset."""
    if not isinstance(superset, dict) or not isinstance(subset, dict):
        return ""

    for key, values in subset.items():
        if key not in superset:
            return str(key)

        if isinstance(values, dict) and isinstance(superset[key], dict):
            key = _invalid_key(superset[key], subset[key])

            if key != "":
                return key

    return ""


# Borrowed from https://stackoverflow.com/a/15836901
def data_merge(superset, subset, recursive=False):
    """Merges subset into superset and return merged result

    The `recursive` flag is just to be able to detect the state for logging msg.

    NOTE: tuples and arbitrary objects are not handled as it is totally
    ambiguous what should happen
    """
    if not recursive:
        logger.info("Merging user settings with default settings.")

    checkkey = _invalid_key(superset, subset)
    if checkkey != "":
        raise ValueError(f"Input contains invalid fields: {checkkey}")

    key = None
    try:
        if superset is None or isinstance(
            superset, (six.string_types, six.integer_types, float)
        ):
            # border case for first run or if a is a primitive
            superset = subset
        elif isinstance(superset, list):
            # lists can be only appended
            if isinstance(subset, list):
                # merge lists
                superset.extend(subset)
            else:
                # append to list
                superset.append(subset)
        elif isinstance(superset, dict):
            # dicts must be merged
            if isinstance(subset, dict):
                for key in subset:
                    if key in superset:
                        superset[key] = data_merge(
                            superset[key], subset[key], recursive=True
                        )
                    else:
                        superset[key] = subset[key]
            else:
                raise ConfigError(
                    f'Cannot merge non-dict "{subset}" into dict "{superset}"'
                )
        else:
            raise ConfigError(f'NOT IMPLEMENTED "{subset}" into "{superset}"')
    except TypeError as err:
        raise ConfigError(
            f"Error '{err}' in key '{key}' when merging '{subset}' into '{superset}'"
        )

    return superset


def config_complete(self):
    """Improving the config to make all sorts of defaults and smart stuff."""

    newcfg = deepcopy(self.config)
    oldcfg = self.config

    prm = self.surfaces["primary"]

    # PLOTSETTINGS
    # ----------------------------------------------------------------------------------
    newcfg_plt = newcfg["plotsettings"]
    oldcfg_plt = oldcfg["plotsettings"]

    ddict = {i: i for i in range(100)}  # just a default dict

    if not oldcfg_plt["wells"]["facieslog"]["colordict"]:
        newcfg_plt["wells"]["facieslog"]["colordict"] = ddict

    if not oldcfg_plt["wells"]["perflog"]["colordict"]:
        newcfg_plt["wells"]["perflog"]["colordict"] = ddict

    if not oldcfg_plt["wells"]["zonelog"]["colordict"]:
        newcfg_plt["wells"]["zonelog"]["colordict"] = ddict

    # PROCESSING SMARTIES
    # ----------------------------------------------------------------------------------
    _zrange = deepcopy(newcfg_plt["design"]["zrange"])
    if not _zrange:
        _zrange = "smart0"

    if isinstance(_zrange, str):
        if _zrange == "smart0":
            newcfg_plt["design"]["zrange"] = _config_smart0_zrange(prm)
        elif _zrange == "smart1":
            newcfg_plt["design"]["zrange"] = _config_smart1_zrange(
                self.wells["wlist"], prm
            )
    elif isinstance(_zrange, dict):
        # process zrange per well, with a global default
        newcfg_plt["design"]["zrange"] = _config_userdefined_zrange(
            self.wells["wlist"], _zrange
        )

    elif isinstance(_zrange, list) and len(_zrange) == 2:
        logger.info("Keep zrange as is")

    else:
        raise RuntimeError("Cannot process/understand the zrange for unknown reasons")

    # Z RANGES
    # ----------------------------------------------------------------------------------
    if self.cube and not newcfg_plt["cube"]["range"]:
        newcfg_plt["cube"]["range"] = [self.cube.values.min(), self.cube.values.max()]

    if self.grid and not newcfg_plt["grid"]["range"]:
        newcfg_plt["grid"]["range"] = [
            self.gridproperty.values.min(),
            self.gridproperty.values.max(),
        ]

    self.config = newcfg


def _config_smart0_zrange(primary):
    """If no zrange is given, try to guess from surfaces"""
    minv = primary[0].values.min()
    maxv = primary[-1].values.max()

    minv = round(minv - 10, -1)
    maxv = round(maxv + 10, -1)

    return [minv, maxv]


def _config_smart1_zrange(wlist, primary):
    minv = primary[0].values.min()
    maxv = primary[-1].values.max()

    minv = round(minv - 10, -1)
    maxv = round(maxv + 10, -1)

    maxwell = minv
    for well in wlist:
        zval = well.dataframe["Z_TVDSS"].values
        maxw = zval.max()
        maxw = round(maxw + 10, -1)
        if maxw > maxwell:
            maxwell = maxw

    if maxwell < maxv:
        maxv = maxwell

    return [minv, maxv]


def _config_userdefined_zrange(wlist: list, _zrange: dict) -> dict:
    zrange_dict = {}

    # first set default
    for well in wlist:
        zrange_dict[well.name] = _zrange["default"]
        logger.info("Default: set %s zrange to %s", well.name, _zrange["default"])

    # well name may be a regular expression
    for wreg, intv in _zrange.items():
        for well in wlist:
            if re.match(wreg + "$", well.name):
                zrange_dict[well.name] = intv
                logger.info(
                    "Override default: set %s zrange to %s, based on regex (%s$)",
                    well.name,
                    intv,
                    wreg,
                )

    return zrange_dict


def _config_default_surf_names(primary):
    """Config default surface name"""
    snames = []
    for ino, _surf in enumerate(primary):
        snames.append("SURF" + str(ino + 1))

    return snames


def update_plotsettings(self, cfg):
    """Update plotsettings and output from the config"""

    # note that 'self' here is a XsectsSettings() instance!

    pcfg = cfg["plotsettings"]

    self.title = cfg["title"]

    self.design_style = pcfg["design"]["style"]
    self.design_zrange = pcfg["design"]["zrange"]
    self.design_gridlines = pcfg["design"]["gridlines"]
    self.design_subtitle = pcfg["design"]["subtitle"]
    self.design_legendsize = pcfg["design"]["legendsize"]
    self.design_legends = pcfg["design"]["legends"]
    self.design_dpi = pcfg["design"]["dpi"]

    self.wellmap_otherwells = pcfg["wellmap"]["otherwells"]
    self.wellmap_expand = pcfg["wellmap"]["expand"]

    self.surf_primary_colors = pcfg["surfaces"]["primary"]["colors"]
    self.surf_primary_fill = pcfg["surfaces"]["primary"]["fill"]

    self.surf_secondary_colors = pcfg["surfaces"]["secondary"]["colors"]
    self.surf_secondary_legend = pcfg["surfaces"]["secondary"]["legend"]

    self.surf_contacts_colors = pcfg["surfaces"]["contacts"]["colors"]

    self.cube_colors = pcfg["cube"]["colors"]
    self.cube_range = pcfg["cube"]["range"]
    self.cube_interpolation = pcfg["cube"]["interpolation"]
    self.cube_alpha = pcfg["cube"]["alpha"]
    self.cube_sampling = pcfg["cube"]["sampling"]

    self.grid_colors = pcfg["grid"]["colors"]
    self.grid_range = pcfg["grid"]["range"]
    self.grid_alpha = pcfg["grid"]["alpha"]
    self.grid_zinc = pcfg["grid"]["zinc"]

    self.wells_zonelog_colors = pcfg["wells"]["zonelog"]["colors"]
    self.wells_zonelog_zoneshift = pcfg["wells"]["zonelog"]["zoneshift"]
    self.wells_zonelog_colordict = pcfg["wells"]["zonelog"]["colordict"]
    self.wells_facieslog_colors = pcfg["wells"]["facieslog"]["colors"]
    self.wells_facieslog_colordict = pcfg["wells"]["facieslog"]["colordict"]
    self.wells_perflog_colors = pcfg["wells"]["perflog"]["colors"]
    self.wells_perflog_colordict = pcfg["wells"]["perflog"]["colordict"]
    self.wells_wellcrossings_show = pcfg["wells"]["wellcrossings"]["show"]
    self.wells_wellcrossings_sampling = pcfg["wells"]["wellcrossings"]["sampling"]
    self.wells_wellcrossings_wfilter = pcfg["wells"]["wellcrossings"]["wfilter"]

    self.output_plotfolder = cfg["output"]["plotfolder"]
    self.output_format = cfg["output"]["format"]
    self.output_prefix = cfg["output"]["prefix"]
    self.output_pdfjoin = cfg["output"]["pdfjoin"]
    self.output_cleanup = cfg["output"]["cleanup"]
