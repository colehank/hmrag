# hmrag

![PyPI version](https://img.shields.io/pypi/v/hmrag.svg)

Hierarchical Multigraph RAG for Conversational Memory

* GitHub: https://github.com/colehank/hmrag/
* PyPI package: https://pypi.org/project/hmrag/
* Created by: **[Guohao Zhang](https://github.com/colehank)** | GitHub https://github.com/colehank | PyPI https://pypi.org/user/colehank/
* Free software: MIT License

## Features

* TODO

## Documentation

Documentation is built with [Zensical](https://zensical.org/) and deployed to GitHub Pages.

* **Live site:** https://colehank.github.io/hmrag/
* **Preview locally:** `just docs-serve` (serves at http://localhost:8000)
* **Build:** `just docs-build`

API documentation is auto-generated from docstrings using [mkdocstrings](https://mkdocstrings.github.io/).

Docs deploy automatically on push to `main` via GitHub Actions. To enable this, go to your repo's Settings > Pages and set the source to **GitHub Actions**.

## Development

To set up for local development:

```bash
# Clone your fork
git clone git@github.com:your_username/hmrag.git
cd hmrag

# Install in editable mode with live updates
uv tool install --editable .
```

This installs the CLI globally but with live updates - any changes you make to the source code are immediately available when you run `hmrag`.

Run tests:

```bash
uv run pytest
```

Run quality checks (format, lint, type check, test):

```bash
just qa
```

## Author

hmrag was created in 2026 by Guohao Zhang.

Built with [Cookiecutter](https://github.com/cookiecutter/cookiecutter) and the [audreyfeldroy/cookiecutter-pypackage](https://github.com/audreyfeldroy/cookiecutter-pypackage) project template.
