"""Private routines for plotting of xsections."""
from __future__ import annotations

import logging
import os
import os.path
import shutil
import subprocess

import pandas as pd

from xtgeoviz.plot import XSection

logger = logging.getLogger(__name__)


def plotting(self):
    """Given the wells, the surfaces, and the config; make plots."""

    pset = self.plotsettings

    if pset.general_engine == "matplotlib":
        _plotting_mpl(self, pset)


# def _plotting_mpl(config, wells, surfaces, outline, cube):
def _plotting_mpl(self, pset):
    """Plotting of xsections with matplotlib.

    Support for polylines and multiwells will come later. It might be
    that instead of calling xtgeo's XSection, a local hidden xsect class here is
    more practical and flexible.
    """

    _folder_work(pset)

    wellcross = _compute_wellcrossings(pset)

    plotfiles = []

    for well in self.wells["wlist"]:
        logger.info("Plot cross section for well %s", well.name)

        if isinstance(pset.design_zrange, dict):
            zrange_min, zrange_max = pset.design_zrange[well.name]
        else:
            zrange_min, zrange_max = pset.design_zrange

        xplot = XSection(
            zmin=zrange_min,
            zmax=zrange_max,
            well=well,
            surfaces=self.surfaces["primary"],
            zonelogshift=pset.wells_zonelog_zoneshift,
            outline=self.outline,
            colormap=pset.surf_primary_colors,
            cube=self.cube,
            grid=self.grid,
            gridproperty=self.gridproperty,
        )

        xplot.colormap_facies = pset.wells_facieslog_colors
        xplot.colormap_facies_dict = pset.wells_facieslog_colordict

        xplot.colormap_perf = pset.wells_perflog_colors
        xplot.colormap_perf_dict = pset.wells_perflog_colordict

        xplot.colormap_zonelog = pset.wells_zonelog_colors
        xplot.colormap_zonelog_dict = pset.wells_zonelog_colordict

        xplot.legendsize = pset.design_legendsize
        xplot.has_legend = pset.design_legends

        if xplot.fence is None:
            continue

        xplot.canvas(title=well.xwellname, subtitle=pset.design_subtitle)

        if self.cube:
            logger.info("Plot cube backdrop")
            vmin, vmax = (None, None)
            if pset.cube_range:
                vmin, vmax = pset.cube_range

            xplot.plot_cube(
                colormap=pset.cube_colors,
                vmin=vmin,
                vmax=vmax,
                alpha=pset.cube_alpha,
                interpolation=pset.cube_interpolation,
                sampling=pset.cube_sampling,
            )

        if self.grid:
            vmin, vmax = (None, None)
            if pset.grid_range:
                vmin, vmax = pset.grid_range

            xplot.plot_grid3d(
                colormap=pset.grid_colors,
                vmin=vmin,
                vmax=vmax,
                alpha=pset.grid_alpha,
                zinc=pset.grid_zinc,
            )

        logger.info("Plot primary surfaces")
        xplot.plot_surfaces(
            fill=pset.surf_primary_fill,
            axisname="main",
            gridlines=True,
            legend=pset.design_legends,
        )

        wcdf = None
        if wellcross is not None:
            wcdf = wellcross.copy()
            wcdf = wcdf.loc[wcdf["WELL"] == well.xwellname]
            del wcdf["WELL"]

        logger.info("Plot well path")
        xplot.plot_well(
            zonelogname=self.wells["zonelog"],
            facieslogname=self.wells["facieslog"],
            perflogname=self.wells["perflog"],
            wellcrossings=wcdf,
        )

        logger.info("Plot primary again (replot, thin lines)")
        xplot.plot_surfaces(
            fill=False, axisname="lines", legend=False, linewidth=0.3, onecolor="black"
        )

        if self.surfaces["contacts"]:
            xplot.plot_surfaces(
                surfaces=self.surfaces["contacts"],
                legendtitle="Contacts",
                colormap=pset.surf_contacts_colors,
                axisname="contacts",
                legend=pset.design_legends,
            )

        if self.surfaces["secondary"]:
            logger.info("Plot secondary surfaces")
            xplot.plot_surfaces(
                surfaces=self.surfaces["secondary"],
                legendtitle=pset.surf_secondary_legend,
                colormap=pset.surf_secondary_colors,
                axisname="second",
                linewidth=2,
                legend=pset.design_legends,
            )

        if pset.design_legends:
            xplot.plot_map()
            xplot.plot_wellmap(
                expand=pset.wellmap_expand, otherwells=pset.wellmap_otherwells
            )

        pname = _save_fig(well, pset, xplot)
        plotfiles.append(pname)

    _collect_pdf(pset, plotfiles)


def _save_fig(well, pset, xplot):
    prefix = ""
    if pset.output_prefix:
        prefix = pset.output_prefix

    pname = os.path.join(
        pset.output_plotfolder, prefix + well.xwellname + "." + pset.output_format
    )

    xplot.savefig(pname, fformat=pset.output_format, dpi=pset.design_dpi)
    logger.info("Plotting xsection for %s to %s", well.wellname, pname)

    if os.environ.get("XTG_SHOW"):
        xplot.show()

    return pname


def _collect_pdf(pset, plotfiles):
    if not pset.output_format == "pdf":
        return

    if pset.output_pdfjoin:
        masterfile = os.path.join([pset.output_plotfolder, pset.output_pdfjoin])

        syscommand = (
            "gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 "
            "-dPDFSETTINGS=/default -dNOPAUSE -dQUIET -dBATCH "
            "-dDetectDuplicateImages -dCompressFonts=true -r150 "
            f"-sOutputFile={masterfile} "
        )

        for pfile in plotfiles:
            syscommand = syscommand + pfile + " "

        logger.info("Collecting PDF files to %s", masterfile)
        logger.info(syscommand)
        ier = subprocess.call(syscommand, shell=True)

        if ier != 0:
            raise RuntimeError(f"Received number != 0 from subprosess: {ier}")

        for pfile in plotfiles:
            os.remove(pfile)


def _folder_work(pset):
    if not os.path.exists(pset.output_plotfolder):
        os.makedirs(pset.output_plotfolder)

    if pset.output_cleanup:
        logger.info("Removing previous files in %s", pset.output_plotfolder)
        try:
            shutil.rmtree(pset.output_plotfolder + "/*")
        except Exception:  # pylint: disable=broad-except
            pass


def _compute_wellcrossings(pset):
    """
    Read CSV with wellcrossing or compute well crossing per well and
    collect to a Pandas dataframe

    Note that self.wells_wellcrossing_show can be a pre generated file, or a bool
    but the bool True is not supported yet...
    """
    dfr = None
    if not pset.wells_wellcrossings_show:
        return dfr

    if isinstance(pset.wells_wellcrossings_show, str):
        dfr = pd.read_csv(pset.wells_wellcrossings_show)

    else:
        raise NotImplementedError("Computing wellcrossing built in not supported yet")

    return dfr
