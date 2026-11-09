"""Private routines for plotting of xsections."""

from __future__ import annotations

import contextlib
import logging
import os
import os.path
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from xtgeoviz.plot import XSection

if TYPE_CHECKING:
    # xsectplotting imports this module, so these owner types must stay type-only.
    import xtgeo

    from .xsectplotting import _Xsections, _XsectSettings

logger: logging.Logger = logging.getLogger(__name__)


def plotting(x_sections: _Xsections) -> None:
    """Render cross-sections using the configured plotting engine.

    Args:
        x_sections: Cross-section application containing loaded objects and settings.
    """

    pset = x_sections.plotsettings

    if pset.general_engine == "matplotlib":
        _plotting_mpl(x_sections, pset)


# def _plotting_mpl(config, wells, surfaces, outline, cube):
def _plotting_mpl(x_sections: _Xsections, pset: _XsectSettings) -> None:
    """Render one matplotlib cross-section per loaded well.

    Adds configured surfaces, well logs, optional cube/grid overlays, maps, and
    output files.

    Args:
        x_sections: Cross-section application containing loaded wells and objects.
        pset: Normalized plot settings and output options.
    """

    _create_or_clean_folder(pset)

    wellcross = _compute_wellcrossings(pset)

    plotfiles = []

    for well in x_sections.wells["wlist"]:
        logger.info("Plot cross section for well %s", well.name)

        if isinstance(pset.design_zrange, dict):
            zrange_min, zrange_max = pset.design_zrange[well.name]
        else:
            zrange_min, zrange_max = pset.design_zrange

        xplot = XSection(
            zmin=zrange_min,
            zmax=zrange_max,
            well=well,
            surfaces=x_sections.surfaces["primary"],
            zonelogshift=pset.wells_zonelog_zoneshift,
            outline=x_sections.outline,
            colormap=pset.surf_primary_colors,
            cube=x_sections.cube,
            grid=x_sections.grid,
            gridproperty=x_sections.gridproperty,
        )

        xplot.colormap_facies = pset.wells_facieslog_colors  # type: ignore[assignment]
        xplot.colormap_facies_dict = pset.wells_facieslog_colordict

        xplot.colormap_perf = pset.wells_perflog_colors  # type: ignore[assignment]
        xplot.colormap_perf_dict = pset.wells_perflog_colordict

        xplot.colormap_zonelog = pset.wells_zonelog_colors  # type: ignore[assignment]
        xplot.colormap_zonelog_dict = pset.wells_zonelog_colordict

        xplot.legendsize = pset.design_legendsize
        xplot.has_legend = pset.design_legends

        if xplot.fence is None:
            continue

        xplot.canvas(title=well.xwellname, subtitle=pset.design_subtitle)

        if x_sections.cube:
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

        if x_sections.grid:
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
            zonelogname=x_sections.wells["zonelog"],
            facieslogname=x_sections.wells["facieslog"],
            perflogname=x_sections.wells["perflog"],
            wellcrossings=wcdf,
        )

        logger.info("Plot primary again (replot, thin lines)")
        xplot.plot_surfaces(
            fill=False, axisname="lines", legend=False, linewidth=0.3, onecolor="black"
        )

        if x_sections.surfaces["contacts"]:
            xplot.plot_surfaces(
                surfaces=x_sections.surfaces["contacts"],
                legendtitle="Contacts",
                colormap=pset.surf_contacts_colors,
                axisname="contacts",
                legend=pset.design_legends,
            )

        if x_sections.surfaces["secondary"]:
            logger.info("Plot secondary surfaces")
            xplot.plot_surfaces(
                surfaces=x_sections.surfaces["secondary"],
                legendtitle=pset.surf_secondary_legend,
                colormap=pset.surf_secondary_colors,
                axisname="second",
                linewidth=2,
                legend=pset.design_legends,
            )

        if pset.design_legends:
            xplot.plot_map()
            xplot.plot_wellmap(
                expand=pset.wellmap_expand,
                otherwells=pset.wellmap_otherwells,  # type: ignore[arg-type]
            )

        pname = _save_fig(well, pset, xplot)
        plotfiles.append(pname)

    _collect_pdf(pset, plotfiles)


def _save_fig(well: xtgeo.Well, pset: _XsectSettings, xplot: XSection) -> str:
    """Save a cross-section figure using the configured output options.

    Args:
        well: Well whose cross-section is being saved.
        pset: Plot settings containing output path, name, format, and DPI.
        xplot: XTGeo cross-section plot object to save.

    Returns:
        Path to the saved figure.
    """
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


def _collect_pdf(pset: _XsectSettings, plotfiles: list[str]) -> None:
    """Optionally combine individual PDF plots and remove their source files.

    Args:
        pset: Plot settings containing the output format and joined PDF name.
        plotfiles: Paths to the per-well plot files.

    Raises:
        RuntimeError: If Ghostscript fails to combine the PDF files.
    """
    if pset.output_format != "pdf":
        return

    if pset.output_pdfjoin:
        masterfile = os.path.join(pset.output_plotfolder, pset.output_pdfjoin)

        command = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/default",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dDetectDuplicateImages",
            "-dCompressFonts=true",
            "-r150",
            f"-sOutputFile={masterfile}",
            *plotfiles,
        ]

        logger.info("Collecting PDF files to %s", masterfile)
        logger.info("Running Ghostscript with arguments: %s", command)
        ier = subprocess.call(command, shell=False)

        if ier != 0:
            raise RuntimeError(f"Received number != 0 from subprosess: {ier}")

        for pfile in plotfiles:
            os.remove(pfile)


def _create_or_clean_folder(pset: _XsectSettings) -> None:
    """Create the output folder and optionally remove its existing contents.

    Args:
        pset: Plot settings containing the folder path and cleanup flag.
    """
    if pset.output_cleanup:
        output_path = Path(pset.output_plotfolder).resolve()
        protected_paths = (Path.cwd().resolve(), Path.home().resolve())
        if output_path.parent == output_path or any(
            output_path == protected_path or output_path in protected_path.parents
            for protected_path in protected_paths
        ):
            raise OSError("Refusing to clean an unsafe output folder")
    if pset.output_cleanup and os.path.realpath(
        pset.output_plotfolder
    ) == os.path.realpath("/tmp"):
        raise OSError("Refusing to clean the shared /tmp output folder")
    if pset.output_cleanup and os.path.islink(pset.output_plotfolder):
        raise OSError("Refusing to clean a symlinked output folder")
    if not os.path.exists(pset.output_plotfolder):
        os.makedirs(pset.output_plotfolder)

    if pset.output_cleanup:
        logger.info("Removing previous files in %s", pset.output_plotfolder)
        for entry in os.listdir(pset.output_plotfolder):
            path = os.path.join(pset.output_plotfolder, entry)
            with contextlib.suppress(Exception):
                if os.path.isdir(path) and not os.path.islink(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)


def _compute_wellcrossings(pset: _XsectSettings) -> pd.DataFrame | None:
    """Read an optional precomputed well-crossing CSV.

    Args:
        pset: Plot settings containing the crossing CSV path or disabled value.

    Returns:
        The CSV contents as a pandas DataFrame, or ``None`` when disabled.

    Raises:
        NotImplementedError: If well crossings are requested with a non-path
            truthy value; computation is not implemented.
    """
    dfr = None
    if not pset.wells_wellcrossings_show:
        return dfr

    if isinstance(pset.wells_wellcrossings_show, str):
        dfr = pd.read_csv(pset.wells_wellcrossings_show)

    else:
        raise NotImplementedError("Computing wellcrossing built in not supported yet")

    return dfr
