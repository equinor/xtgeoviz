"""Config option for xsections"""

from __future__ import annotations

import logging
import re
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Literal, overload

import yaml

if TYPE_CHECKING:
    import xtgeo

    # xsectplotting imports this module, so its owner types must stay type-only.
    from .xsectplotting import _Xsections, _XsectSettings

logger: logging.Logger = logging.getLogger(__name__)

DEFAULT_CONFIG: str = """
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
        fromgrid: No
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


@overload
def config_defaults(as_yaml: Literal[True] = True) -> str: ...


@overload
def config_defaults(as_yaml: Literal[False]) -> dict[str, Any]: ...


def config_defaults(as_yaml: bool = True) -> str | dict[str, Any]:
    """Return the complete default cross-section configuration.

    Args:
        as_yaml: If true, return the YAML text; otherwise, return the parsed mapping.

    Returns:
        The default configuration as YAML text or a nested dictionary.
    """
    logger.info("Configure default settings with as_yaml set to: %s", as_yaml)
    if as_yaml:
        return DEFAULT_CONFIG

    return yaml.safe_load(DEFAULT_CONFIG)


def _invalid_key(superset: object, subset: object) -> str:
    """Find the first key present in ``subset`` but absent from ``superset``.

    The check recurses into values that are dictionaries on both sides.

    Args:
        superset: Mapping that defines the accepted configuration keys.
        subset: Mapping whose keys are being validated.

    Returns:
        The first invalid key converted to a string, or an empty string when
        all checked keys are valid or either value is not a dictionary.
    """
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
def data_merge(superset: Any, subset: Any, recursive: bool = False) -> Any:
    """Merge configuration values from ``subset`` into ``superset``.

    Dictionary values are merged recursively. Existing lists are extended (or
    appended to when ``subset`` is not a list); scalar defaults are replaced.
    Dictionary and list supersets may be mutated in place.

    Args:
        superset: Default or existing value to merge into.
        subset: User-provided value that overrides or extends the default.
        recursive: Whether this call is part of a nested merge, used to limit
            top-level logging.

    Returns:
        The merged value. For mutable dictionary or list inputs, this may be
        the same object as ``superset``.

    Raises:
        ValueError: If a dictionary contains keys absent from the default mapping.
        ConfigError: If the values cannot be merged or the superset type is unsupported.
    """
    if not recursive:
        logger.info("Merging user settings with default settings.")

    checkkey = _invalid_key(superset, subset)
    if checkkey != "":
        raise ValueError(f"Input contains invalid fields: {checkkey}")

    key = None
    try:
        if superset is None or isinstance(superset, (str, int, float)):
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


def config_complete(x_sections: _Xsections) -> None:
    """Complete settings that depend on the loaded cross-section data.

    Fills empty color dictionaries and derives depth, cube, and grid ranges from
    the loaded surfaces, wells, and volumes.

    Args:
        x_sections: Cross-section application holding config and loaded objects.
    """

    newcfg = deepcopy(x_sections.config)
    oldcfg = x_sections.config

    prm = x_sections.surfaces["primary"]

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
                x_sections.wells["wlist"], prm
            )
    elif isinstance(_zrange, dict):
        # process zrange per well, with a global default
        newcfg_plt["design"]["zrange"] = _config_userdefined_zrange(
            x_sections.wells["wlist"], _zrange
        )

    elif isinstance(_zrange, list) and len(_zrange) == 2:
        logger.info("Keep zrange as is")

    else:
        raise RuntimeError("Cannot process/understand the zrange for unknown reasons")

    # Z RANGES
    # ----------------------------------------------------------------------------------
    if x_sections.cube and not newcfg_plt["cube"]["range"]:
        newcfg_plt["cube"]["range"] = [
            x_sections.cube.values.min(),
            x_sections.cube.values.max(),
        ]

    if x_sections.grid and not newcfg_plt["grid"]["range"]:
        newcfg_plt["grid"]["range"] = [
            x_sections.gridproperty.values.min(),
            x_sections.gridproperty.values.max(),
        ]

    x_sections.config = newcfg


def _config_smart0_zrange(primary: list[xtgeo.RegularSurface]) -> list[float]:
    """Estimate a depth range from the first and last primary surfaces.

    Args:
        primary: Ordered primary surfaces used to establish the shallow and
            deep limits.

    Returns:
        A two-item range expanded by ten units and rounded to tens.
    """
    minv = primary[0].values.min()
    maxv = primary[-1].values.max()

    minv = round(minv - 10, -1)
    maxv = round(maxv + 10, -1)

    return [minv, maxv]


def _config_smart1_zrange(
    wlist: list[xtgeo.Well], primary: list[xtgeo.RegularSurface]
) -> list[float]:
    """Estimate a surface depth range and cap it using the well paths.

    Args:
        wlist: Wells whose ``Z_TVDSS`` samples constrain the maximum depth.
        primary: Ordered primary surfaces used to establish the initial range.

    Returns:
        A two-item depth range expanded and rounded to tens, capped by the
        deepest rounded well sample when it is shallower than the final surface.
    """
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


def _config_userdefined_zrange(
    wlist: list[xtgeo.Well], _zrange: dict[str, object]
) -> dict[str, object]:
    """Resolve default and regex-specific depth ranges for each well.

    Args:
        wlist: Wells to assign ranges to.
        _zrange: Mapping with a ``default`` range and optional regex-keyed
            overrides.

    Returns:
        A mapping from well names to their selected depth ranges.
    """
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


def _config_default_surf_names(primary: list[xtgeo.RegularSurface]) -> list[str]:
    """Generate sequential display names for a list of surfaces.

    Args:
        primary: Surfaces to create names for.

    Returns:
        Names in the form ``SURF1``, ``SURF2``, and so on.
    """
    snames = []
    for ino, _surf in enumerate(primary):
        snames.append("SURF" + str(ino + 1))

    return snames


def update_plotsettings(settings: _XsectSettings, cfg: dict[str, Any]) -> None:
    """Copy normalized plotting and output options onto the settings object.

    Args:
        settings: Plot settings object to update.
        cfg: Complete merged configuration mapping.
    """

    pcfg = cfg["plotsettings"]

    settings.title = cfg["title"]

    settings.design_style = pcfg["design"]["style"]
    settings.design_zrange = pcfg["design"]["zrange"]
    settings.design_gridlines = pcfg["design"]["gridlines"]
    settings.design_subtitle = pcfg["design"]["subtitle"]
    settings.design_legendsize = pcfg["design"]["legendsize"]
    settings.design_legends = pcfg["design"]["legends"]
    settings.design_dpi = pcfg["design"]["dpi"]

    settings.wellmap_otherwells = pcfg["wellmap"]["otherwells"]
    settings.wellmap_expand = pcfg["wellmap"]["expand"]

    settings.surf_primary_colors = pcfg["surfaces"]["primary"]["colors"]
    settings.surf_primary_fill = pcfg["surfaces"]["primary"]["fill"]

    settings.surf_secondary_colors = pcfg["surfaces"]["secondary"]["colors"]
    settings.surf_secondary_legend = pcfg["surfaces"]["secondary"]["legend"]

    settings.surf_contacts_colors = pcfg["surfaces"]["contacts"]["colors"]

    settings.cube_colors = pcfg["cube"]["colors"]
    settings.cube_range = pcfg["cube"]["range"]
    settings.cube_interpolation = pcfg["cube"]["interpolation"]
    settings.cube_alpha = pcfg["cube"]["alpha"]
    settings.cube_sampling = pcfg["cube"]["sampling"]

    settings.grid_colors = pcfg["grid"]["colors"]
    settings.grid_range = pcfg["grid"]["range"]
    settings.grid_alpha = pcfg["grid"]["alpha"]
    settings.grid_zinc = pcfg["grid"]["zinc"]

    settings.wells_zonelog_colors = pcfg["wells"]["zonelog"]["colors"]
    settings.wells_zonelog_zoneshift = pcfg["wells"]["zonelog"]["zoneshift"]
    settings.wells_zonelog_colordict = pcfg["wells"]["zonelog"]["colordict"]
    settings.wells_facieslog_colors = pcfg["wells"]["facieslog"]["colors"]
    settings.wells_facieslog_colordict = pcfg["wells"]["facieslog"]["colordict"]
    settings.wells_perflog_colors = pcfg["wells"]["perflog"]["colors"]
    settings.wells_perflog_colordict = pcfg["wells"]["perflog"]["colordict"]
    settings.wells_wellcrossings_show = pcfg["wells"]["wellcrossings"]["show"]
    settings.wells_wellcrossings_sampling = pcfg["wells"]["wellcrossings"]["sampling"]
    settings.wells_wellcrossings_wfilter = pcfg["wells"]["wellcrossings"]["wfilter"]

    settings.output_plotfolder = cfg["output"]["plotfolder"]
    settings.output_format = cfg["output"]["format"]
    settings.output_prefix = cfg["output"]["prefix"]
    settings.output_pdfjoin = cfg["output"]["pdfjoin"]
    settings.output_cleanup = cfg["output"]["cleanup"]
