"""Module for fast XSection plots of wells/surfaces etc, using matplotlib."""

from __future__ import annotations

import logging
import math
import warnings
from typing import Any, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import numpy.ma as ma
import pandas as pd
import xtgeo
from matplotlib import collections as mc
from matplotlib.colors import Colormap, LinearSegmentedColormap, ListedColormap
from matplotlib.lines import Line2D

from ._libwrapper import (
    matplotlib_colormap,
    matplotlib_set_xticks,
    scipy_gaussianfilter,
)
from .baseplot import BasePlot

logger: logging.Logger = logging.getLogger(__name__)


class XSection(BasePlot):
    """Class for plotting a cross-section of a well.

    Args:
        zmin: Upper level of the plot (top Y axis).
        zmax (float): Lower level of the plot (bottom Y axis).
        well: XTGeo well object.
        surfaces: List of XTGeo RegularSurface objects
        surfacenames: List of surface names (str) for legend
        cube: A XTGeo Cube instance
        grid: A XTGeo Grid instance
        gridproperty: A XTGeo GridProperty instance
        colormap: Name of colormap, e.g. 'Set1'. Default is 'xtgeo'
        outline: XTGeo Polygons object

    """

    def __init__(
        self,
        zmin: float | None = 0,
        zmax: float | None = 9999,
        well: Optional[xtgeo.Well] = None,
        surfaces: Optional[list[xtgeo.RegularSurface]] = None,
        sampling: Optional[int] = 20,
        nextend: Optional[int] = 5,
        colormap: Optional[Union[str, LinearSegmentedColormap, ListedColormap]] = None,
        zonelogshift: Optional[int] = 0,
        surfacenames: Optional[list[str]] = None,
        cube: Optional[xtgeo.Cube] = None,
        grid: Optional[xtgeo.Grid] = None,
        gridproperty: Optional[xtgeo.GridProperty] = None,
        outline: Optional[xtgeo.Polygons] = None,
    ) -> None:
        """Init method."""
        super().__init__()

        self._zmin = zmin
        self._zmax = zmax
        self._well = well
        self._nextend = nextend
        self._sampling = sampling
        self._surfaces = surfaces
        self._surfacenames = surfacenames
        self._cube = cube
        self._grid = grid
        self._gridproperty = gridproperty
        self._zonelogshift = zonelogshift
        self._outline = outline

        self._has_axes = True
        self._has_legend = True

        self._pagesize = "A4"
        self._fence: np.ndarray | None = None
        self._legendtitle = "Zones"
        self._legendsize = 5

        self._ax1: dict[str, plt.Axes] | plt.Axes | None = None
        self._ax2: plt.Axes | None = None
        self._ax3: plt.Axes | None = None
        self._allfigs = []

        self._colormap_cube: Colormap | None = None
        self._colorlegend_cube = False

        self._colormap_grid: Colormap | None = None
        self._colorlegend_grid = False

        if colormap is None:
            self._colormap = matplotlib_colormap("viridis")
        elif isinstance(colormap, (LinearSegmentedColormap, ListedColormap)):
            self._colormap = colormap
        else:
            self.define_colormap(colormap)

        self._colormap_facies: Colormap = self.define_any_colormap("xtgeo")
        self._colormap_facies_dict: dict[int, int | str] = {
            idx: idx for idx in range(100)
        }

        self._colormap_perf: Colormap = self.define_any_colormap("xtgeo")
        self._colormap_perf_dict: dict[int, int | str] = {
            idx: idx for idx in range(100)
        }

        self._colormap_zonelog: Colormap | None = None
        self._colormap_zonelog_dict: dict[int, int | str] = {
            idx: idx for idx in range(100)
        }
        logger.debug("Initialized XSection instance")

    # ==================================================================================
    # Properties
    # Notice additonal props in base class
    # ==================================================================================
    @property
    def pagesize(self) -> str:
        """Returns page size."""
        return self._pagesize

    @property
    def legendsize(self) -> int:
        """Returns or set the legend size."""
        return self._legendsize

    @legendsize.setter
    def legendsize(self, lsize: int) -> None:
        self._legendsize = lsize

    @property
    def has_legend(self) -> bool:
        """Returns or set the legends."""
        return self._has_legend

    @has_legend.setter
    def has_legend(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise ValueError("Input is not a bool")

        self._has_legend = value

    @property
    def has_axes(self) -> bool:
        """Returns or set the axes status."""
        return self._has_axes

    @has_axes.setter
    def has_axes(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise ValueError("Input is not a bool")

        self._has_axes = value

    @property
    def colormap_facies(self) -> Colormap:
        """Set or get the facies colormap."""
        return self._colormap_facies

    @colormap_facies.setter
    def colormap_facies(self, cmap: str) -> None:
        self._colormap_facies = self.define_any_colormap(cmap)

    @property
    def colormap_zonelog(self) -> Colormap | None:
        """Set or get the zonelog colormap."""
        return self._colormap_zonelog

    @colormap_zonelog.setter
    def colormap_zonelog(self, cmap: str) -> None:
        self._colormap_zonelog = self.define_any_colormap(cmap)

    @property
    def colormap_perf(self) -> Colormap:
        """Set or get the perforations colormap."""
        return self._colormap_perf

    @colormap_perf.setter
    def colormap_perf(self, cmap: str) -> None:
        self._colormap_perf = self.define_any_colormap(cmap)

    @property
    def colormap_facies_dict(self) -> dict[int, int | str]:
        """Set or get the facies colormap actual dict table."""
        return self._colormap_facies_dict

    @colormap_facies_dict.setter
    def colormap_facies_dict(self, xdict: dict[int, int | str]) -> None:
        if not isinstance(xdict, dict):
            raise ValueError("Input is not a dict")
        self._colormap_facies_dict = xdict

    @property
    def colormap_perf_dict(self) -> dict[int, int | str]:
        """Set or get the perf colormap actual dict table."""
        return self._colormap_perf_dict

    @colormap_perf_dict.setter
    def colormap_perf_dict(self, xdict: dict[int, int | str]) -> None:
        if not isinstance(xdict, dict):
            raise ValueError("Input is not a dict")
        self._colormap_perf_dict = xdict

    @property
    def colormap_zonelog_dict(self) -> dict[int, int | str]:
        """Set or get the zonelog colormap actual dict table."""
        return self._colormap_zonelog_dict

    @colormap_zonelog_dict.setter
    def colormap_zonelog_dict(self, xdict: dict[int, int | str]) -> None:
        if not isinstance(xdict, dict):
            raise ValueError("Input is not a dict")
        self._colormap_zonelog_dict = xdict

    @property
    def fence(self) -> np.ndarray | None:
        """Set or get the fence spesification."""
        if self._fence is None:
            if self._well is not None:
                wfence = self._well.get_fence_polyline(
                    sampling=self._sampling, nextend=self._nextend, tvdmin=self._zmin
                )
                self._fence = wfence

                if wfence is False:
                    self._fence = None
            else:
                raise ValueError("Input well is None")  # should be more flexible
        return self._fence

    @fence.setter
    def fence(self, myfence: np.ndarray | None) -> None:
        # this can be extended with checks and various types of input...
        self._fence = myfence

    # ==================================================================================
    # Functions methods (public)
    # ==================================================================================

    def canvas(
        self,
        title: str | None = None,
        subtitle: str | None = None,
        infotext: str | None = None,
        figscaling: float = 1.0,
    ) -> None:
        """Prepare the canvas to plot on, with title and subtitle.

        Args:
            title (str, optional): Title of plot.
            subtitle (str, optional): Sub title of plot.
            infotext (str, optional): Text to be written as info string.
            figscaling (str, optional): Figure scaling, default is 1.0


        """
        # overriding the base class canvas

        plt.rcParams["axes.xmargin"] = 0  # fill the plot margins

        if not self._has_axes:
            plt.rcParams["axes.titlecolor"] = (0, 0, 0, 0)
            plt.rcParams["axes.edgecolor"] = (0, 0, 0, 0)
            plt.rcParams["axes.labelcolor"] = (0, 0, 0, 0)
            plt.rcParams["axes.titlecolor"] = (0, 0, 0, 0)
            plt.rcParams["xtick.color"] = (0, 0, 0, 0)
            plt.rcParams["ytick.color"] = (0, 0, 0, 0)

        self._fig = plt.figure(figsize=(11.69 * figscaling, 8.27 * figscaling))
        self._allfigs.append(self._fig)

        ax1 = {
            "main": plt.subplot2grid((20, 28), (0, 0), rowspan=20, colspan=23),
        }

        ax2 = plt.subplot2grid(
            (20, 28), (10, 23), rowspan=5, colspan=5, frame_on=self._has_legend
        )

        ax3 = plt.subplot2grid(
            (20, 28), (15, 23), rowspan=5, colspan=5, frame_on=self._has_legend
        )

        if self._has_legend:
            # indicate A to B
            plt.text(
                0.02,
                0.98,
                "A",
                ha="left",
                va="top",
                transform=ax1["main"].transAxes,
                fontsize=8,
            )
            plt.text(
                0.98,
                0.98,
                "B",
                ha="right",
                va="top",
                transform=ax1["main"].transAxes,
                fontsize=8,
            )

        # title here:
        if title is not None:
            plt.text(
                0.5,
                1.09,
                title,
                ha="center",
                va="center",
                transform=ax1["main"].transAxes,
                fontsize=18,
            )

        if subtitle is not None:
            ax1["main"].set_title(subtitle, size=14)

        if infotext is not None:
            plt.text(
                -0.11,
                -0.11,
                infotext,
                ha="left",
                va="center",
                transform=ax1["main"].transAxes,
                fontsize=6,
            )

        ax1["main"].set_ylabel("Depth", fontsize=12.0)
        ax1["main"].set_xlabel("Length along well", fontsize=12)

        ax2.tick_params(
            axis="both",
            which="both",
            bottom=False,
            top=False,
            right=False,
            left=False,
            labelbottom=False,
            labeltop=False,
            labelright=False,
            labelleft=False,
        )

        ax3.tick_params(
            axis="both",
            which="both",
            bottom=False,
            top=False,
            right=False,
            left=False,
            labelbottom=False,
            labeltop=False,
            labelright=False,
            labelleft=False,
        )

        # need these also, a bug in functions above?
        ax2.xaxis.set_major_formatter(plt.NullFormatter())
        ax2.yaxis.set_major_formatter(plt.NullFormatter())
        ax3.xaxis.set_major_formatter(plt.NullFormatter())
        ax3.yaxis.set_major_formatter(plt.NullFormatter())

        self._ax1 = ax1
        self._ax2 = ax2
        self._ax3 = ax3

    def plot_well(
        self,
        zonelogname: str | None = "ZONELOG",
        facieslogname: str | None = None,
        perflogname: str | None = None,
        wellcrossings: pd.DataFrame | None = None,
        wellcrossingnames: bool = True,
        wellcrossingyears: bool = False,
        welltrajcolor: Any = "black",
        welltrajwidth: float = 6,
    ) -> None:
        """Input an XTGeo Well object and plot it."""
        if self._well is None:
            raise ValueError("Input well is None")
        if self.fence is None:
            return

        # reduce the well data by Pandas operations
        dfr = self._well.get_dataframe(copy=False)
        self._well.set_dataframe(dfr[dfr["Z_TVDSS"] > self._zmin])

        # Create a relative XYLENGTH vector (0.0 where well starts)
        self._well.create_relative_hlen()

        dfr = self._well.get_dataframe(copy=False)
        if dfr.empty:
            self._showok = False
            return

        # get the well trajectory (numpies) as copy
        zv = dfr["Z_TVDSS"].values.copy()
        hv = dfr["R_HLEN"].values.copy()

        # plot the perflog, if any, first
        if perflogname:
            ax, bba = self._currentax(axisname="perf")
            self._plot_well_perflog(dfr, ax, bba, perflogname, legend=self._has_legend)

        # plot the facies, if any, behind the trajectory; ie. first or second
        if facieslogname:
            ax, bba = self._currentax(axisname="facies")
            self._plot_well_faclog(dfr, ax, bba, facieslogname, legend=self._has_legend)

        axx, _bbxa = self._currentax(axisname="well")
        self._plot_well_traj(
            axx, zv, hv, welltrajcolor=welltrajcolor, linewidth=welltrajwidth
        )

        if zonelogname:
            ax, bba = self._currentax(axisname="main")
            self._plot_well_zlog(dfr, axx, bba, zonelogname, legend=self._has_legend)

        if wellcrossings is not None and wellcrossings.empty:
            wellcrossings = None

        if wellcrossings is not None:
            self._plot_well_crossings(
                dfr, axx, wellcrossings, wellcrossingnames, wellcrossingyears
            )

    def set_xaxis_md(self, gridlines: bool = False) -> None:
        """Set x-axis labels to measured depth."""
        if self._well is None:
            raise ValueError("Input well is None")
        md_start = float(self._well.get_dataframe(copy=False)["MDEPTH"].iloc[0])
        md_start_round = int(math.floor(md_start / 100.0)) * 100
        md_start_delta = md_start - md_start_round

        ax, _ = self._currentax(axisname="main")
        auto_ticks = ax.get_xticks()
        auto_ticks_delta = auto_ticks[1] - auto_ticks[0]
        lim = ax.get_xlim()

        new_ticks: list[float] = []
        new_tick_labels: list[str] = []
        delta = 0
        for tick in auto_ticks:
            new_ticks.append(int(float(tick) - md_start_delta))
            new_tick_labels.append(str(int(md_start_round + delta)))
            delta += auto_ticks_delta

        # Set new xticks and labels
        matplotlib_set_xticks(ax, new_ticks, new_tick_labels)

        if gridlines:
            ax.tick_params(axis="y", direction="in", which="both")
            ax.minorticks_on()
            ax.grid(color="black", linewidth=0.8, which="major", linestyle="-")
            ax.grid(color="black", linewidth=0.5, which="minor", linestyle="--")

        # Restore xaxis limits and set axis title
        ax.set_xlim(lim)
        ax.set_ylabel("TVD MSL [m]", fontsize=12.0)
        ax.set_xlabel("Measured Depth [m]", fontsize=12)

    def _plot_well_traj(
        self,
        ax: Any,
        zv: np.ndarray,
        hv: np.ndarray,
        welltrajcolor: Any,
        linewidth: float,
    ) -> None:
        """Plot the trajectory as a black line."""
        zv_copy = ma.masked_where(zv < self._zmin, zv)
        hv_copy = ma.masked_where(zv < self._zmin, hv)

        ax.plot(hv_copy, zv_copy, linewidth=linewidth, c=welltrajcolor)

    @staticmethod
    def _line_segments_colors(
        df: pd.DataFrame,
        idx: dict[int, int | str],
        ctable: list[tuple[float, float, float, float]],
        logname: str,
        fillnavalue: Any,
    ) -> tuple[list[list[Any]], np.ndarray]:
        """Get segment and color array for plotting matplotlib lineCollection."""
        df_idx = pd.DataFrame(
            {"idx_log": list(idx.keys()), "idx_color": list(idx.values())}
        )

        df_ctable = df_idx.merge(
            pd.DataFrame({"ctable": ctable}),
            how="left",
            left_on="idx_color",
            right_index=True,
        )

        dff = df.merge(df_ctable, how="left", left_on=logname, right_on="idx_log")

        dff["point"] = list(zip(dff["R_HLEN"], dff["Z_TVDSS"]))

        # find line segments
        segments: list[list[Any]] = []
        segments_i = -1
        colorlist: list[Any] = []
        previous_color = None

        for point, color in zip(dff["point"], dff["ctable"]):
            if np.any(np.isnan(color)):
                color = fillnavalue

            if color == previous_color:
                segments[segments_i].append(point)
                previous_color = color
            else:
                # add endpoint to current segment
                if segments_i > 0:
                    segments[segments_i].append(point)

                # start new segment
                segments.append([point])
                colorlist.append(color)

                previous_color = color
                segments_i += 1

        return segments, np.asarray(colorlist, dtype=object)

    def _plot_well_zlog(
        self,
        df: pd.DataFrame,
        ax: plt.Axes,
        bba: tuple[float, ...],
        zonelogname: str,
        logwidth: float = 4,
        legend: bool = False,
    ) -> None:
        """Plot the zone log as colored segments."""
        if zonelogname not in df.columns:
            return

        zomin = 0
        zomax = 0

        try:
            zomin = int(df[zonelogname].min())
            zomax = int(df[zonelogname].max())
        except ValueError:
            self._showok = False
            return

        logger.debug("ZOMIN, ZOMAX %s %s ?", zomin, zomax)  # used for what?

        zshift = self._zonelogshift or 0

        if self.colormap_zonelog is not None:
            cmap = self.colormap_zonelog
            ctable = self.get_any_colormap_as_table(cmap)
        else:
            ctable = self.get_colormap_as_table()

        idx = self.colormap_zonelog_dict

        # adjust for zoneshift.
        idx_zshift = {}
        for key in idx:
            idx_zshift[key - zshift + 1] = idx[key]

        fillnavalue = (0.9, 0.9, 0.9)
        segments, segments_colors = self._line_segments_colors(
            df, idx_zshift, ctable, zonelogname, fillnavalue
        )

        lc = mc.LineCollection(
            segments, colors=segments_colors, linewidth=logwidth, zorder=202
        )

        ax.add_collection(lc)

        if legend:
            if self._well is None:
                return
            zrecord = self._well.get_logrecord(zonelogname)
            zrecord = {val: zname for val, zname in zrecord.items() if val >= 0}

            zcolors: dict[str, Any] = {}
            for zone in zrecord:
                color_index = idx[zone]
                zcolors[zrecord[zone]] = (
                    color_index if isinstance(color_index, str) else ctable[color_index]
                )

            self._drawproxylegend(ax, bba, items=zcolors, title="Zonelog")

    def _plot_well_faclog(
        self,
        df: pd.DataFrame,
        ax: plt.Axes,
        bba: tuple[float, ...],
        facieslogname: str,
        logwidth: float = 9,
        legend: bool = True,
    ) -> None:
        """Plot the facies log as colored segments.

        Args:
            df (dataframe): The Well dataframe.
            ax (axes): The ax plot object.
            bba: Bounding box
            facieslogname (str): name of the facies log.
            logwidth (int): Log linewidth.
            legend (bool): Plot log legend?
        """
        if facieslogname not in df.columns:
            return

        cmap = self.colormap_facies
        ctable = self.get_any_colormap_as_table(cmap)
        idx = self.colormap_facies_dict

        fillnavalue = (0, 0, 0, 0)  # transparent
        segments, segments_colors = self._line_segments_colors(
            df, idx, ctable, facieslogname, fillnavalue
        )

        lc = mc.LineCollection(
            segments, colors=segments_colors, linewidth=logwidth, zorder=201
        )

        ax.add_collection(lc)

        if legend:
            if self._well is None:
                return
            frecord = self._well.get_logrecord(facieslogname)
            frecord = {val: fname for val, fname in frecord.items() if val >= 0}

            fcolors: dict[str, Any] = {}
            for facies in frecord:
                color_index = idx[facies]
                if isinstance(color_index, str):
                    color: Any = color_index
                else:
                    color = ctable[color_index]

                fcolors[frecord[facies]] = color

            self._drawproxylegend(ax, bba, items=fcolors, title="Facies")

    def _plot_well_perflog(
        self,
        df: pd.DataFrame,
        ax: plt.Axes,
        bba: tuple[float, ...],
        perflogname: str,
        logwidth: float = 12,
        legend: bool = True,
    ) -> None:
        """Plot the perforation log as colored segments.

        Args:
            df (dataframe): The Well dataframe.
            ax (axes): The ax plot object.
            zv (ndarray): The numpy Z TVD array.
            bba: Boundinng box
            hv (ndarray): The numpy Length  array.
            perflogname (str): name of the perforation log.
            logwidth (int): Log linewidth.
            legend (bool): Plot log legend?
        """
        if perflogname not in df.columns:
            return

        cmap = self.colormap_perf
        ctable = self.get_any_colormap_as_table(cmap)
        idx = self.colormap_perf_dict

        fillnavalue = (0, 0, 0, 0)  # transparent
        segments, segments_colors = self._line_segments_colors(
            df, idx, ctable, perflogname, fillnavalue
        )

        lc = mc.LineCollection(
            segments, colors=segments_colors, linewidth=logwidth, zorder=200
        )

        ax.add_collection(lc)

        if legend:
            if self._well is None:
                return
            precord = self._well.get_logrecord(perflogname)
            precord = {val: pname for val, pname in precord.items() if val >= 0}

            pcolors: dict[str, Any] = {}
            for perf in precord:
                color_index = idx[perf]
                pcolors[precord[perf]] = (
                    color_index if isinstance(color_index, str) else ctable[color_index]
                )

            self._drawproxylegend(ax, bba, items=pcolors, title="Perforations")

    @staticmethod
    def _plot_well_crossings(
        dfr: pd.DataFrame,
        ax: plt.Axes,
        wcross: pd.DataFrame,
        names: bool = True,
        years: bool = False,
    ) -> None:
        """Plot well crossing based on dataframe (wcross).

        The well crossing coordinates are identified for this well,
        and then it is looking for the closest coordinate. Given this
        coordinate, a position is chosen.

        The pandas dataframe wcross shall have the following columns:

        * Name of crossing wells named CWELL
        * Coordinate X named X_UTME
        * Coordinate Y named Y_UTMN
        * Coordinate Z named Z_TVDSS

        Optional column:
        * Drilled year of crossing well named CYEAR

        Args:
            dfr: Well dataframe
            ax: current axis
            wcross: A pandas dataframe with precomputed well crossings
            names: Display the names of the crossed wells
            years: Display the drilled year of the crossed wells
        """
        placings = {
            0: (40, 40),
            1: (40, -20),
            2: (-30, 30),
            3: (30, 20),
            4: (-40, 30),
            5: (-20, 40),
        }

        for index, row in wcross.iterrows():
            xcoord = row.X_UTME
            ycoord = row.Y_UTMN

            dfrc = dfr.copy()

            dfrc["DLEN"] = pow(
                pow(dfrc.X_UTME - xcoord, 2) + pow(dfrc.Y_UTMN - ycoord, 2), 0.5
            )

            minindx = dfrc.DLEN.idxmin()

            ax.scatter(
                dfrc.R_HLEN[minindx],
                row.Z_TVDSS,
                marker="o",
                color="black",
                s=70,
                zorder=300,
            )
            ax.scatter(
                dfrc.R_HLEN[minindx],
                row.Z_TVDSS,
                marker="o",
                color="orange",
                s=38,
                zorder=302,
            )

            modulo = index % 5

            text = ""
            if names:
                text = xtgeo.Well.get_short_wellname(row.CWELL)

            if years:
                text = text + "\n" + row.CYEAR if names else row.CYEAR

            if names or years:
                ax.annotate(
                    text,
                    size=6,
                    xy=(dfrc.R_HLEN[minindx], row.Z_TVDSS),
                    xytext=placings[modulo],
                    textcoords="offset points",
                    arrowprops={
                        "arrowstyle": "->",
                        "connectionstyle": "angle3,angleA=0,angleB=90",
                    },
                    color="black",
                )

    def _drawproxylegend(
        self,
        ax: plt.Axes,
        bba: tuple[float, ...],
        items: dict[str, Any],
        title: str | None = None,
    ) -> None:
        proxies = []
        labels = []

        for item in items:
            color = items[item]
            proxies.append(Line2D([0, 1], [0, 1], color=color, linewidth=5))
            labels.append(item)

        ax.legend(
            proxies,
            labels,
            loc="upper left",
            bbox_to_anchor=bba,
            prop={"size": self._legendsize},
            title=title,
            handlelength=2,
        )

    def _drawlegend(
        self, ax: plt.Axes, bba: tuple[float, ...], title: str | None = None
    ) -> None:
        leg = ax.legend(
            loc="upper left",
            bbox_to_anchor=bba,
            prop={"size": self._legendsize},
            title=title,
            handlelength=2,
        )

        for myleg in leg.get_lines():
            myleg.set_linewidth(5)

    def _currentax(self, axisname: str = "main") -> tuple[plt.Axes, tuple[float, ...]]:
        """Keep track of current axis; is needed as one new legend need one new axis."""
        # for multiple legends, bba is dynamic
        bbapos = {
            "main": (1.22, 1.12, 1, 0),
            "contacts": (1.01, 1.12),
            "second": (1.22, 0.50),
            "facies": (1.01, 1.00),
            "perf": (1.22, 0.45),
        }

        if not isinstance(self._ax1, dict):
            raise ValueError("Canvas must be initialized before plotting")
        ax1 = self._ax1

        if axisname != "main":
            ax1[axisname] = self._ax1["main"].twinx()

            # invert min,max to invert the Y axis
            ax1[axisname].set_ylim(self._zmax, self._zmin)

            ax1[axisname].set_yticklabels([])
            ax1[axisname].tick_params(axis="y", direction="in")

        ax = self._ax1[axisname]

        bba = bbapos.get(axisname, (1.22, 0.5))

        return ax, bba

    def plot_cube(
        self,
        colormap: str | None = "seismic",
        vmin: float | None = None,
        vmax: float | None = None,
        alpha: float = 0.7,
        interpolation: str = "gaussian",
        sampling: str = "nearest",
    ) -> None:
        """Plot a cube backdrop.

        Args:
            colormap (ColorMap): Name of color map (default 'seismic')
            vmin (float): Minimum value in plot.
            vmax (float); Maximum value in plot
            alpha (float): Alpah blending number beween 0 and 1.
            interpolation (str): Interpolation for plotting, cf. matplotlib
                documentation on this. Also gaussianN is allowed, where
                N = 1..9.
            sampling (str): 'nearest' (default) or 'trilinear' (more precise)

        Raises:
            ValueError: No cube is loaded

        """
        if self.fence is None:
            return

        if self._cube is None:
            raise ValueError("Ask for plot cube, but noe cube is loaded")

        ax, _ = self._currentax(axisname="main")

        zinc = self._cube.zinc / 2.0

        zvv = self._cube.get_randomline(
            self.fence,
            zmin=self._zmin,
            zmax=self._zmax,
            zincrement=zinc,
            sampling=sampling,
        )

        h1, h2, v1, v2, arr = zvv

        if self._colormap_cube is None:
            if colormap is None:
                colormap = "seismic"
            self._colormap_cube = self.define_any_colormap(colormap)

        if "gaussian" in interpolation:  # allow gaussian3 etc
            try:
                sigma = int(interpolation[-1])
                arr = scipy_gaussianfilter(arr, sigma)
                interpolation = "none"
            except ValueError:
                interpolation = "gaussian"

        img = ax.imshow(
            arr,
            cmap=self._colormap_cube,
            interpolation=interpolation,
            vmin=vmin,
            vmax=vmax,
            extent=(h1, h2, v2, v1),
            aspect="auto",
            alpha=alpha,
        )

        # steer this?
        if self._colorlegend_cube:
            self._fig.colorbar(img, ax=ax)

    def plot_grid3d(
        self,
        colormap: str | None = "rainbow",
        vmin: float | None = None,
        vmax: float | None = None,
        alpha: float = 0.7,
        zinc: float = 0.5,
        interpolation: str = "auto",
    ) -> None:
        """Plot a sampled grid with gridproperty backdrop.

        Args:
            colormap (ColorMap): Name of color map (default 'rainbow')
            vmin (float): Minimum value in plot.
            vmax (float); Maximum value in plot
            alpha (float): Alpha blending number beween 0 and 1.
            zinc (float): Sampling vertically, default is 0.5
            interpolation (str): Interpolation for plotting, cf. matplotlib
                documentation on this. "auto" uses "nearest" for discrete
                parameters and "antialiased" for floats.

        Raises:
            ValueError: No grid or gridproperty is loaded

        """
        if self.fence is None:
            return

        if self._grid is None or self._gridproperty is None:
            raise ValueError("Ask for plot of grid, but no grid is loaded")

        ax, _bba = self._currentax(axisname="main")

        zvv = self._grid.get_randomline(
            self.fence,
            self._gridproperty,
            zmin=self._zmin,
            zmax=self._zmax,
            zincrement=zinc,
        )

        h1, h2, v1, v2, arr = zvv

        if self._colormap_grid is None:
            if colormap is None:
                colormap = "rainbow"
            self._colormap_grid = self.define_any_colormap(colormap)

        if interpolation == "auto":
            if self._gridproperty.isdiscrete:
                interpolation = "nearest"
            else:
                interpolation = "antialiased"

        img = ax.imshow(
            arr,
            cmap=self._colormap_grid,
            vmin=vmin,
            vmax=vmax,
            extent=(h1, h2, v2, v1),
            aspect="auto",
            alpha=alpha,
            interpolation=interpolation,
        )

        # steer this?
        if self._colorlegend_grid:
            self._fig.colorbar(img, ax=ax)

    def plot_surfaces(
        self,
        fill: bool = False,
        surfaces: list[xtgeo.RegularSurface] | None = None,
        surfacenames: list[str] | None = None,
        colormap: str | None = None,
        onecolor: Any = None,
        linewidth: float = 1.0,
        linestyle: str = "-",
        legend: bool = True,
        legendtitle: str | None = None,
        fancyline: bool = False,
        axisname: str = "main",
        gridlines: bool = False,
    ) -> None:
        """Input a surface list (ordered from top to base) , and plot them."""
        if self.fence is None:
            return

        ax, bba = self._currentax(axisname=axisname)

        # either use surfaces from __init__, or override with surfaces
        # speciefied here
        if surfaces is None:
            surfaces = self._surfaces
            surfacenames = self._surfacenames
        if surfaces is None:
            raise ValueError("No surfaces are available to plot")

        surfacenames = [surf.name for surf in surfaces]

        if legendtitle is None:
            legendtitle = self._legendtitle

        if colormap is not None:
            self.define_colormap(colormap)

        nlen = len(surfaces)

        # legend
        slegend = []
        if surfacenames is None:
            for i in range(nlen):
                slegend.append(f"Surf {i}")

        else:
            # do a check
            if len(surfacenames) != nlen:
                msg = (
                    "Wrong number of entries in surfacenames! "
                    "Number of names is {} while number of files "
                    "is {}".format(len(surfacenames), nlen)
                )
                raise ValueError(msg)

            slegend = surfacenames

        if nlen > self._colormap.N:
            raise ValueError(
                f"Too few colors in color table ({self._colormap.N}) "
                f"vs number of surfaces ({nlen})"
            )

        # sample the horizon to the fence:
        colortable = self.get_colormap_as_table()
        for i in range(nlen):
            usecolor = colortable[i]
            if onecolor:
                usecolor = onecolor
            if not fill:
                hfence = surfaces[i].get_randomline(self.fence)
                xcol = "white"
                if fancyline:
                    cxx = usecolor
                    if cxx[0] + cxx[1] + cxx[2] > 1.5:
                        xcol = "black"
                    ax.plot(
                        hfence[:, 0], hfence[:, 1], linewidth=1.2 * linewidth, c=xcol
                    )
                ax.plot(
                    hfence[:, 0],
                    hfence[:, 1],
                    linewidth=linewidth,
                    c=usecolor,
                    label=slegend[i],
                    linestyle=linestyle,
                )
                if fancyline:
                    ax.plot(
                        hfence[:, 0], hfence[:, 1], linewidth=0.3 * linewidth, c=xcol
                    )
            else:
                # need copy() .. why?? found by debugging...
                hfence1 = surfaces[i].get_randomline(self.fence).copy()
                x1 = hfence1[:, 0]
                y1 = hfence1[:, 1]
                if i < (nlen - 1):
                    hfence2 = surfaces[i + 1].get_randomline(self.fence).copy()
                    y2 = hfence2[:, 1]
                else:
                    y2 = y1.copy()

                ax.plot(
                    x1, y1, linewidth=0.1 * linewidth, linestyle=linestyle, c="black"
                )
                ax.fill_between(x1, y1, y2, facecolor=colortable[i], label=slegend[i])

        # invert min,max to invert the Y axis
        ax.set_ylim(self._zmax, self._zmin)

        if legend:
            self._drawlegend(ax, bba, title=legendtitle)

        if axisname != "main":
            ax.set_yticklabels([])

        ax.tick_params(axis="y", direction="in")

        if axisname == "main" and gridlines:
            ax.grid(color="grey", linewidth=0.2)

    def plot_md_data(
        self,
        data: pd.DataFrame,
        markersize: int | float = 10,
        color: Any = "red",
        linestyle: str = "",
        label: str | bool = False,
        zorder: int | float = 350,
        **kwargs: Any,
    ) -> None:
        """Plot MD vs TVD data as lines and/or markers.

        The input pandas dataframe points shall have the following columns:
        * Name of well(s) named WELL
        * Coordinate X named MDEPTH
        * Coordinate Y named Z_TVDSS
        """
        ax, _ = self._currentax(axisname="main")

        well = self._well
        if well is None:
            raise ValueError("Input well is None")
        data_well = data.copy()
        data_well = data_well.loc[data_well["WELL"] == well.xwellname]
        del data_well["WELL"]

        md_start = well.get_dataframe(copy=False)["MDEPTH"].iloc[0]
        data_well["R_HLEN"] = data_well["MDEPTH"]
        data_well["R_HLEN"] = data_well["R_HLEN"].subtract(md_start)

        data_well.plot(
            ax=ax,
            x="R_HLEN",
            y="Z_TVDSS",
            legend=None,
            linestyle=linestyle,
            markersize=markersize,
            color=color,
            label=label,
            zorder=zorder,
            **kwargs,
        )

    def plot_wellmap(
        self, otherwells: list[xtgeo.Polygons] | None = None, expand: float = 1
    ) -> None:
        """Plot well map as local view, optionally with nearby wells.

        Args:
            otherwells (list of Polygons): List of surrounding wells to plot,
                these wells are repr as Polygons instances, one per well.
            expand (float): Plot axis expand factor (default is 1); larger
                values may be used if other wells are plotted.


        """
        if self._ax2 is None:
            raise ValueError("Canvas must be initialized before plotting")
        if self._well is None:
            raise ValueError("Input well is None")
        ax = self._ax2
        fence = self.fence

        if fence is not None:
            xwellarray = self._well.get_dataframe(copy=False)["X_UTME"].values
            ywellarray = self._well.get_dataframe(copy=False)["Y_UTMN"].values

            ax.plot(xwellarray, ywellarray, linewidth=4, c="cyan")

            ax.plot(fence[:, 0], fence[:, 1], linewidth=1, c="black")
            ax.annotate("A", xy=(fence[0, 0], fence[0, 1]), fontsize=8)
            ax.annotate("B", xy=(fence[-1, 0], fence[-1, 1]), fontsize=8)
            ax.set_aspect("equal", "datalim")

            left, right = ax.get_xlim()
            xdiff = right - left
            bottom, top = ax.get_ylim()
            ydiff = top - bottom

            ax.set_xlim(left - (expand - 1.0) * xdiff, right + (expand - 1.0) * xdiff)
            ax.set_ylim(bottom - (expand - 1.0) * ydiff, top + (expand - 1.0) * ydiff)
        if otherwells:
            for poly in otherwells:
                if not isinstance(poly, xtgeo.Polygons):
                    warnings.warn(
                        f"<otherw> not a Polygons instance, but a {type(poly)}",
                        UserWarning,
                    )
                    continue
                if poly.name == self._well.xwellname:
                    continue
                xwp = poly.get_dataframe(copy=False)[poly.xname].values
                ywp = poly.get_dataframe(copy=False)[poly.yname].values
                ax.plot(xwp, ywp, linewidth=1, c="grey")
                ax.annotate(poly.name, xy=(xwp[-1], ywp[-1]), color="grey", size=5)

    def plot_map(self) -> None:
        """Plot well location map as an overall view (with field outline)."""
        if self.fence is None:
            return

        if self._outline is None:
            return

        if self._ax3 is None:
            raise ValueError("Canvas must be initialized before plotting")
        ax = self._ax3
        fence = self.fence
        if fence is not None:
            xp = self._outline.get_dataframe(copy=False)["X_UTME"].values
            yp = self._outline.get_dataframe(copy=False)["Y_UTMN"].values
            ip = self._outline.get_dataframe(copy=False)["POLY_ID"].values

            ax.plot(fence[:, 0], fence[:, 1], linewidth=3, c="red")

            for i in range(int(ip.min()), int(ip.max()) + 1):
                xpc = xp.copy()[ip == i]
                ypc = yp.copy()[ip == i]
                if len(xpc) > 1:
                    ax.plot(xpc, ypc, linewidth=0.3, c="black")

            ax.set_aspect("equal", "datalim")
