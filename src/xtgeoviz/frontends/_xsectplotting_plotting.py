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

    app_config = getattr(x_sections, "config", {})
    input_config = app_config.get("input", {}) if isinstance(app_config, dict) else {}
    input_paths: list[Path] = []

    def add_input_path(value: object) -> None:
        if isinstance(value, (str, os.PathLike)) and value:
            input_paths.append(Path(value))

    wells_config = input_config.get("wells", {})
    if isinstance(wells_config, dict):
        add_input_path(wells_config.get("folder"))

    surface_config = input_config.get("surfaces", {})
    if isinstance(surface_config, dict):
        add_input_path(surface_config.get("fromgrid"))
        for surface_name in ("primary", "secondary", "contacts"):
            surface_set = surface_config.get(surface_name, {})
            if isinstance(surface_set, dict):
                add_input_path(surface_set.get("folder"))

    add_input_path(input_config.get("outline"))
    add_input_path(input_config.get("cube"))

    grid_config = input_config.get("grid", {})
    if isinstance(grid_config, dict):
        add_input_path(grid_config.get("geometry"))
        property_config = grid_config.get("property", {})
        if isinstance(property_config, dict):
            add_input_path(property_config.get("file"))
    wells = x_sections.wells.get("wlist", [])
    if pset.output_format == "pdf" and pset.output_pdfjoin:
        prefix = pset.output_prefix or ""
        plotfiles = [
            os.path.join(pset.output_plotfolder, f"{prefix}{well.xwellname}.pdf")
            for well in wells
        ]
        masterfile = os.path.join(pset.output_plotfolder, pset.output_pdfjoin)
        _validate_pdf_join_paths(masterfile, plotfiles)

    _create_or_clean_folder(pset, input_paths)

    wellcross = _compute_wellcrossings(pset)

    plotfiles = []

    for well in wells:
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
        ValueError: If the joined PDF destination overlaps a source PDF.
    """
    if pset.output_format != "pdf":
        return

    if pset.output_pdfjoin:
        masterfile = os.path.join(pset.output_plotfolder, pset.output_pdfjoin)
        _validate_pdf_join_paths(masterfile, plotfiles)

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


def _validate_pdf_join_paths(masterfile: str, plotfiles: list[str]) -> None:
    """Reject a joined PDF destination that aliases one of its input files.

    Args:
        masterfile: Joined PDF destination.
        plotfiles: Per-well PDF inputs.

    Raises:
        ValueError: If the output resolves to an input or shares its inode.
    """
    output_path = Path(masterfile)
    input_paths = [Path(plotfile) for plotfile in plotfiles]
    resolved_output = output_path.resolve()
    if resolved_output in {input_path.resolve() for input_path in input_paths} or (
        output_path.exists()
        and any(
            input_path.exists() and output_path.samefile(input_path)
            for input_path in input_paths
        )
    ):
        raise ValueError("Joined PDF output path overlaps a source PDF")


def _create_or_clean_folder(
    pset: _XsectSettings,
    input_paths: list[str | os.PathLike[str]] | None = None,
) -> None:
    """Create the output folder and optionally remove its existing contents.

    Args:
        pset: Plot settings containing the folder path and cleanup flag.
        input_paths: Configured input paths protected from output cleanup.
    """
    if pset.output_cleanup:
        output_path = Path(pset.output_plotfolder).resolve()
        protected_paths = (Path.cwd().resolve(), Path.home().resolve())
        if output_path.parent == output_path or any(
            output_path == protected_path or output_path in protected_path.parents
            for protected_path in protected_paths
        ):
            raise OSError("Refusing to clean an unsafe output folder")
        for input_path in input_paths or []:
            resolved_input_path = Path(input_path).resolve()
            if (
                output_path == resolved_input_path
                or output_path.is_relative_to(resolved_input_path)
                or resolved_input_path.is_relative_to(output_path)
            ):
                raise OSError("Refusing to clean a folder overlapping configured input")
    if pset.output_cleanup and os.path.realpath(
        pset.output_plotfolder
    ) == os.path.realpath("/tmp"):
        raise OSError("Refusing to clean the shared /tmp output folder")
    if pset.output_cleanup and os.path.islink(os.path.normpath(pset.output_plotfolder)):
        raise OSError("Refusing to clean a symlinked output folder")

    wellcrossings_path = getattr(pset, "wells_wellcrossings_show", None)
    if pset.output_cleanup and isinstance(wellcrossings_path, str):
        output_path = Path(pset.output_plotfolder)
        input_path = Path(wellcrossings_path)
        resolved_output_path = output_path.resolve()
        resolved_input_path = input_path.resolve()
        if input_path.is_relative_to(output_path) or resolved_input_path.is_relative_to(
            resolved_output_path
        ):
            raise OSError(
                "Refusing to clean output folder containing well-crossings CSV"
            )

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
