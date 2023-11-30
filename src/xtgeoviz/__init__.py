# flake8: noqa
from xtgeoviz.frontends import xsectplotting
from xtgeoviz.frontends.xsectplotting import xsectplot
from xtgeoviz.plot.quickplot import quickplot

try:
    from .version import version

    __version__ = version
except ImportError:
    __version__ = "0.0.0"
