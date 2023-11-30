"""Making cross sections (plots), primarely wells."""
from __future__ import annotations

import argparse
import json
import logging
import os.path
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

import yaml

from . import _xsectplotting_config as _cfg
from . import _xsectplotting_load as _load
from . import _xsectplotting_plotting as _plt

APPNAME = "xtgeoviz.xsectplot"

logger = logging.getLogger(__name__)


def _prettyprint(anydict):
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
    design_zrange: Union[tuple, list, dict] = (1000, 2000)
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

    cube_colors: str = "seismic"
    cube_range: Any = None
    cube_interpolation: str = "gaussian"
    cube_alpha: float = 0.8
    cube_sampling: str = "nearest"

    wells_zonelog_colors: str = "random40"
    wells_zonelog_zoneshift: int = 0
    wells_zonelog_colordict: dict = field(default_factory=dict, init=False)
    wells_facieslog_colors: str = "xtgeo"
    wells_facieslog_colordict: dict = field(default_factory=dict, init=False)
    wells_perflog_colors: str = "xtgeo"
    wells_perflog_colordict: dict = field(default_factory=dict, init=False)
    wells_wellcrossings_show: bool = False
    wells_wellcrossings_sampling: int = 20
    wells_wellcrossings_wfilter: int = 5

    output_plotfolder: str = "/tmp"
    output_format: str = "svg"
    output_prefix: str = ""
    output_pdfjoin: bool = False
    output_cleanup: bool = False

    def __post_init__(self):
        logger.info("Initilize class: %s", __class__.__name__)

    def update_plotsettings(self, config):
        logger.info("Update plotsettings")
        _cfg.update_plotsettings(self, config)


@dataclass
class _Xsections:
    """Private class for XSections plotting"""

    args: Optional[list] = None
    inputdata: dict = field(default_factory=dict)
    psettings: dict = field(default_factory=dict)
    output: dict = field(default_factory=dict)
    verbosity: str | None = None

    config: dict = field(default_factory=dict, init=False)  # resulting YAML config
    polylines: list = field(default_factory=list, init=False)
    multiwells: list = field(default_factory=list, init=False)  # list of multiwells
    wells: dict = field(default_factory=dict, init=False)
    cube: Any = field(default=None, init=False)
    grid: Any = field(default=None, init=False)
    gridproperty: Any = field(default=None, init=False)
    outline: Any = field(default=None, init=False)
    contacts: Any = field(default=None, init=False)
    surfaces: dict = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.args = None  # command line args
        self.plotsettings = _XsectSettings()  # plotsettings

        if not self.inputdata:
            self.parse_args()
        else:
            self.parse_dicts()

    def parse_args(self):
        """Parse the command line arguments."""
        parser = argparse.ArgumentParser(
            description="Make beautiful cross sections in seconds",
            usage="xsections --config some.yaml ... ",
        )

        parser.add_argument(
            "-c", "--config", dest="config", type=str, help="Config file on YAML format"
        )

        if self.args is None:
            self.args = sys.argv[1:]

        if len(self.args) < 2:
            parser.print_help()
            print("QUIT")
            sys.exit(0)

        self.args = parser.parse_args(self.args)

    def set_logger_verbosity(self):
        """Use config setting to set eventual logging output."""

        actual_verbosity = "normal"
        if self.verbosity:
            actual_verbosity = self.verbosity
        else:
            actual_verbosity = self.config["verbosity"]

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

    def parse_config(self):
        """Read config from YAML and oveeride with defaults."""

        args = self.args
        inputfile = args.config

        ydefaults = _cfg.config_defaults()

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

    def parse_dicts(self):
        """Parse settings from dicts given as arguments, and merge with defaults."""
        default = _cfg.config_defaults(as_yaml=False)
        # _prettyprint(default)
        update = {
            "input": self.inputdata,
            "plotsettings": self.psettings,
            "output": self.output,
        }
        self.config = _cfg.data_merge(default, update)
        self.set_logger_verbosity()
        # _prettyprint(self.config)

    def load_wells(self):
        """Load wells as a list of XTGeo Well() instances"""

        _load.load_wells(self)

    def load_surfaces(self):
        """Load surfaces as a dict of lists of XTGeo Surface() instances"""

        _load.load_surfaces(self)

    def load_cube(self):
        """Load cube to plot as backdrop, a XTGeo Cube() instances"""

        _load.load_cube(self)

    def load_grid(self):
        """Load grid with property to plot as backdrop, XTGeo Grid() + GridProperty
        instances.
        """

        _load.load_grid(self)

    def load_outline(self):
        """Load map outline to plot as info"""

        _load.load_outline(self)

    def config_complete(self):
        """improve config, better defaults, and some smart settings based on input"""

        _cfg.config_complete(self)  # config, wells, surfs["primary"])

    def plot(self):
        """Do the actual plotting"""

        _plt.plotting(self)


# ======================================================================================
# MAIN
# ======================================================================================


def xsectplot(
    args: Optional[Dict] = None,
    inputdata: Optional[Dict] = None,
    plotsettings: Optional[Dict] = None,
    output: Optional[Dict] = None,
    verbosity: Optional[str] = None,
):
    """Frontend function for plotting xsections.

    The input can either be in form of command line args parsing a YAML file with
    additional command line args that overides, or it can be dicts in form of inputdata,
    plotsettings and output that will be combined with defaults.

    If the input key is not None, then any args will be ignored.

    Args:
        args: Command line args
        input: A dictionary spesifying minimum required input
        plotsettings: A dictionary spesifying minimum required plotsettings
        output: A dictionary spesyfying minimum required output settings
        verbosity: Default None means that it is set from the config; otherwise a
            string here will override: "normal" for normal output, "info" for using
            logging for all modules, and similarly "debug"
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
