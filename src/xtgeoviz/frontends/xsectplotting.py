"""Making cross sections (plots), primarely wells."""

from __future__ import annotations

import argparse
import json
import logging
import os.path
import sys
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, cast

import yaml

from . import (
    _xsectplotting_config as _cfg,
    _xsectplotting_load as _load,
    _xsectplotting_plotting as _plt,
)

APPNAME: str = "xtgeoviz.xsectplot"

logger: logging.Logger = logging.getLogger(__name__)


def _prettyprint(anydict: Any) -> None:
    """Print a value as indented JSON when it is serializable.

    Args:
        anydict: Value to serialize and print.
    """
    try:
        print(json.dumps(anydict, indent=4, ensure_ascii=False))
    except TypeError:
        print("Cannot serialize to JSON...")


@dataclass
class _XsectSettings:
    """Class for storing plot settings for the plots"""

    title: str = "Generic Title"

    general_engine: str = "matplotlib"

    design_style: int = 1
    design_zrange: tuple[int | float, ...] | list[int | float] | dict[str, Any] = (
        1000,
        2000,
    )
    design_gridlines: str = "both"
    design_subtitle: Optional[str] = None
    design_legendsize: int = 6
    design_legends: bool = True
    design_dpi: int = 100

    wellmap_otherwells: bool = False
    wellmap_expand: int = 2

    surf_primary_colors: str = "random40"
    surf_primary_fill: bool = True

    surf_contacts_colors: str = "rainbow"

    # surfaces secondary:
    surf_secondary_colors: str = "xtgeo"
    surf_secondary_legend: str = "?"

    grid_colors: str = "rainbow"
    grid_range: list[int | float] | tuple[int | float, ...] | None = None
    grid_alpha: float = 0.8
    grid_zinc: float = 0.5

    cube_colors: str = "seismic"
    cube_range: list[int | float] | tuple[int | float, ...] | None = None
    cube_interpolation: str = "gaussian"
    cube_alpha: float = 0.8
    cube_sampling: str = "nearest"

    wells_zonelog_colors: str = "random40"
    wells_zonelog_zoneshift: int = 0
    wells_zonelog_colordict: dict[int, int | str] = field(
        default_factory=dict, init=False
    )
    wells_facieslog_colors: str = "xtgeo"
    wells_facieslog_colordict: dict[int, int | str] = field(
        default_factory=dict, init=False
    )
    wells_perflog_colors: str = "xtgeo"
    wells_perflog_colordict: dict[int, int | str] = field(
        default_factory=dict, init=False
    )
    wells_wellcrossings_show: bool | str = False
    wells_wellcrossings_sampling: int = 20
    wells_wellcrossings_wfilter: int = 5

    output_plotfolder: str = "/tmp"
    output_format: str = "svg"
    output_prefix: str = ""
    output_pdfjoin: str | Literal[False] = False
    output_cleanup: bool = False

    def __post_init__(self) -> None:
        """Log initialization of the plot settings object."""
        logger.info("Initilize class: %s", type(self).__name__)

    def update_plotsettings(self, config: dict[str, Any]) -> None:
        """Populate plot settings from the merged configuration.

        Args:
            config: Complete configuration mapping produced by the frontend.
        """
        logger.info("Update plotsettings")
        _cfg.update_plotsettings(self, config)


@dataclass
class _Xsections:
    """Private class for XSections plotting"""

    args: list[str] | argparse.Namespace | None = None
    inputdata: dict[str, Any] | None = field(default_factory=dict)
    psettings: dict[str, Any] | None = field(default_factory=dict)
    output: dict[str, Any] | None = field(default_factory=dict)
    verbosity: str | None = None

    config: dict[str, Any] = field(default_factory=dict, init=False)
    polylines: list[Any] = field(default_factory=list, init=False)
    multiwells: list[Any] = field(default_factory=list, init=False)
    wells: dict[str, Any] = field(default_factory=dict, init=False)
    cube: Any = field(default=None, init=False)
    grid: Any = field(default=None, init=False)
    gridproperty: Any = field(default=None, init=False)
    outline: Any = field(default=None, init=False)
    contacts: Any = field(default=None, init=False)
    surfaces: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Create plot settings and parse CLI or dictionary input."""
        self.plotsettings = _XsectSettings()  # plotsettings

        if not self.inputdata:
            self.parse_args()
            self.parse_config()
        else:
            self.parse_dicts()

    def parse_args(self) -> None:
        """Parse command-line arguments and store the resulting namespace.

        Reads arguments from ``sys.argv`` and requires a config option and path.

        Raises:
            SystemExit: If arguments are incomplete or argument parsing fails.
        """
        parser = argparse.ArgumentParser(
            description="Make beautiful cross sections in seconds",
            usage="xsections --config some.yaml ... ",
        )

        parser.add_argument(
            "-c", "--config", dest="config", type=str, help="Config file on YAML format"
        )

        args = sys.argv[1:] if self.args is None else cast("list[str]", self.args)

        if len(args) < 2:
            parser.print_help()
            print("QUIT")
            sys.exit(0)

        self.args = parser.parse_args(args)

    def set_logger_verbosity(self) -> None:
        """Configure logging from the explicit or configured verbosity."""

        actual_verbosity = self.verbosity or self.config["verbosity"]

        if actual_verbosity == "silent":
            logging.basicConfig(
                level=logging.WARNING,
                stream=sys.stdout,
                format="%(asctime)s %(levelname)s:%(message)s",
            )
            for handler in logging.root.handlers:
                handler.addFilter(logging.Filter("xtgeoviz"))

        elif actual_verbosity == "info":
            logging.basicConfig(
                level=logging.INFO,
                stream=sys.stdout,
                format="%(asctime)s %(levelname)s:%(message)s",
            )
            for handler in logging.root.handlers:
                handler.removeFilter(logging.Filter("xtgeoviz"))

        else:  # normal
            logging.basicConfig(
                level=logging.INFO,
                stream=sys.stdout,
                format=">> %(message)s",
            )
            for handler in logging.root.handlers:
                handler.addFilter(logging.Filter("xtgeoviz"))

    def parse_config(self) -> None:
        """Read a YAML config file and merge it over the defaults.

        Raises:
            OSError: If the configured file does not exist.
            ValueError: If the YAML contains keys not present in the defaults.
        """
        args = cast("argparse.Namespace", self.args)
        inputfile = args.config

        ydefaults = cast("str", _cfg.config_defaults())

        dconfig = yaml.safe_load(ydefaults)

        if not os.path.isfile(inputfile):
            raise OSError(f"No such config file exists: {inputfile}")

        with open(inputfile, encoding="utf-8") as stream:
            config = yaml.safe_load(stream)

        # merge config with defaults:
        merged = _cfg.data_merge(dconfig, config)

        self.config = merged
        self.set_logger_verbosity()

        logger.info("Input config YAML file <%s> is read...", inputfile)

    def parse_dicts(self) -> None:
        """Merge Python dictionary inputs into the default configuration."""
        default = _cfg.config_defaults(as_yaml=False)
        # _prettyprint(default)
        update = {
            "input": self.inputdata or {},
            "plotsettings": self.psettings or {},
            "output": self.output or {},
        }
        self.config = _cfg.data_merge(default, update)
        self.set_logger_verbosity()
        # _prettyprint(self.config)

    def load_wells(self) -> None:
        """Load configured well objects and well-log settings."""

        _load.load_wells(self)

    def load_surfaces(self) -> None:
        """Load configured primary, secondary, and contact surfaces."""

        _load.load_surfaces(self)

    def load_cube(self) -> None:
        """Load the configured cube or use a supplied XTGeo cube object."""

        _load.load_cube(self)

    def load_grid(self) -> None:
        """Load configured grid geometry and its property for plotting."""

        _load.load_grid(self)

    def load_outline(self) -> None:
        """Load the configured field outline or a supplied polygons object."""

        _load.load_outline(self)

    def config_complete(self) -> None:
        """Fill derived settings using the loaded wells, surfaces, and volumes."""

        _cfg.config_complete(self)  # config, wells, surfs["primary"])

    def plot(self) -> None:
        """Render cross-sections using the loaded data and plot settings."""
        _plt.plotting(self)


# ======================================================================================
# MAIN
# ======================================================================================


def xsectplot(
    args: list[str] | None = None,
    inputdata: dict[str, Any] | None = None,
    plotsettings: dict[str, Any] | None = None,
    output: dict[str, Any] | None = None,
    verbosity: Optional[str] = None,
) -> None:
    """Create cross-section plots from YAML configuration or Python mappings.

    When ``inputdata`` is truthy, the ``inputdata``, ``plotsettings``, and
    ``output`` mappings are merged with defaults. Otherwise, configuration is
    read from command-line arguments.

    Args:
        args: Optional command-line tokens to parse. When omitted and dictionary
            input is not provided, command-line parsing reads ``sys.argv``.
        inputdata: Input sources such as wells, surfaces, cube, outline, and grid.
        plotsettings: Overrides for design, colors, ranges, and overlays.
        output: Output folder, format, PDF, and cleanup settings.
        verbosity: Optional logging level override; otherwise the config value is used.

    Returns:
        None.

    Raises:
        OSError: If the selected YAML config file does not exist.
        ValueError: If a supplied configuration contains invalid keys.
        SystemExit: If command-line arguments are incomplete or invalid.
    """

    app = _Xsections(args, inputdata, plotsettings, output, verbosity)

    # load what to xsect (and show):
    app.load_wells()
    app.load_surfaces()
    app.load_cube()
    app.load_outline()

    app.config_complete()

    app.plotsettings.update_plotsettings(app.config)

    app.plot()


if __name__ == "__main__":
    xsectplot()
