import pathlib

import pytest

import xtgeoviz.plot._colortables as ct

TPATH = pathlib.Path("../xtgeo-testdata")


class TestColorTables:
    """Tests for built-in and file-based color tables."""

    def test_readfromfile(self) -> None:
        """Read color table from RMS file."""
        cfile = TPATH / "etc/colortables/colfacies.txt"
        ctable = ct.colorsfromfile(str(cfile))
        assert ctable[5] == (0.49019608, 0.38431373, 0.05882353)

    def test_xtgeo_colors(self) -> None:
        """Read the XTGeo color table."""
        ctable = ct.xtgeocolors()
        assert ctable[5] == (0.000, 1.000, 1.000)

    def test_randomc_returns_requested_rgb_colors(self) -> None:
        """Return the requested number of RGB tuples with normalized values."""
        ctable = ct.randomc(20)

        assert len(ctable) == 20
        assert all(
            len(color) == 3 and all(0.0 <= component <= 1.0 for component in color)
            for color in ctable
        )

    def test_randomc_returns_empty_table_for_zero_length(self) -> None:
        """Return an empty color table when no entries are requested."""
        assert ct.randomc(0) == []

    def test_colorsfromfile_raises_for_missing_file(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Raise an I/O error when the requested color-table file is missing."""
        missing_file = tmp_path / "missing-color-table.txt"

        with pytest.raises(OSError, match="Color file not found"):
            ct.colorsfromfile(str(missing_file))

    def test_colorsfromfile_rejects_malformed_color_entry(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Reject a recognized color entry without numeric RGB components."""
        malformed_file = tmp_path / "malformed-color-table.txt"
        malformed_file.write_text(
            "ColorMap.color(0) = red green blue\n", encoding="utf-8"
        )

        with pytest.raises(ValueError):
            ct.colorsfromfile(str(malformed_file))
