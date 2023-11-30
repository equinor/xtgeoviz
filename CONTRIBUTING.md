# Contributing

All contributions are welcome. You can contribute in many ways.

## Report Bugs

Report bugs at
[https://github.com/equinor/xtgeoviz/issues](https://github.com/equinor/xtgeoviz/issues).
When reporting a bug please include:

- Your operating system name and version
- Your Python version and version of relevant packages (e.g. matplotlib)
- Any other details about your local setup that might be helpful in
  troubleshooting
- Detailed steps to reproduce the bug

## Fix Bugs

Look through the git issues for bugs. Anything tagged with "bug"
and "help wanted" is open to whomever wants to implement it.

## Implement Features

Look through the git issues for feature requests or ideas.
Anything tagged with "enhancement" and "help wanted" is open
to whomever wants to implement it.

## Write Documentation

xtgeoviz could always use more documentation, whether as part of the
official xtgeoviz documentation pages or in docstrings.

## Submit Feedback

The best way to send feedback is to create an issue at
[https://github.com/equinor/xtgeoviz/issues](https://github.com/equinor/xtgeoviz/issues).

If you are proposing a feature:

- Explain in detail how it would work
- Keep the scope as narrow as possible, to make it easier to implement
- Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

## Get Started!

Ready to contribute? Here's how to set up `xtgeoviz` for local development.

1. Fork this repository to your GitHub account
2. Clone your fork locally:
   ```sh
    git clone git@github.com:<your-user>/xtgeoviz.git
    ```
3. Install your local copy into a virtual environment:
    ```sh
    python -m venv your-venv
    source your-venv/bin/activate
    cd xtgeoviz/
    pip install ".[dev,docs]"
    ```
4. Create a feature branch for local development:
    ```sh
    git checkout -b name-of-your-bugfix-or-feature
    ```
   Now you can make your changes locally.
5. When you're done making changes, check that your changes pass flake8,
   black, isort, mypy, and the tests:
   ```sh
   black src tests
   isort src tests
   flake8 src tests
   mypy src
   pytest
   ```
6. Commit your changes and push your branch to GitHub:
   ```sh
   git add your-changed file-names
   git commit -m "Your detailed description of your changes."
   git push origin name-of-your-bugfix-or-feature
   ```
7. Create a pull request

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.md.
