# xtgeoviz

[![tests](https://github.com/equinor/xtgeoviz/actions/workflows/ci-xtgeoviz.yml/badge.svg)](https://github.com/equinor/xtgeoviz/actions/workflows/ci-xtgeoviz.yml)
![Python Version](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13.svg)
[![License: LGPL v3](https://img.shields.io/github/license/equinor/fmu-tools)](https://www.gnu.org/licenses/lgpl-3.0)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI](https://img.shields.io/pypi/v/xtgeoviz.svg)](https://pypi.org/project/xtgeoviz/)

Utility functions for plotting xtgeo objects.

## Install

xtgeoviz is available from PyPI.

```sh
pip install xtgeoviz
```

### Dependency compatibility

xtgeoviz supports current releases of XTGeo, Matplotlib, SciPy, and its other
dependencies. Older releases are not supported and may not provide APIs used by
xtgeoviz. The dependency declarations do not prevent an installer from selecting
an older release, including when another package constrains it.

If an import or plotting operation fails because of an incompatible dependency,
upgrade the affected package, for example:

```sh
pip install --upgrade xtgeo matplotlib scipy
```

The project lockfile is used for reproducible development and CI; scheduled CI
also tests updated dependencies.

## Usage

```python
import xtgeoviz.plot as xtgplot
import xtgeo

surf = xtgeo.surface_from_file("somemap.gri")
xtgplot.quickplot(surf)
```

## Documentation

The documentation can be found at
[https://equinor.github.io/xtgeoviz](https://equinor.github.io/xtgeoviz).

## Developing & Contributing

All contributions are welcome. Please see the
[Contributing document](https://equinor.github.io/xtgeoviz/contributing.html)
for more details and instructions for getting started.

## License

This software is released under the LGPLv3 license.
