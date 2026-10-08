"""Sphinx configuration for pyWellSFMUI documentation."""

import re
from pathlib import Path

_INIT = Path(__file__).resolve().parents[1] / "src" / "pywellsfmui" / "__init__.py"

project = "pyWellSFMUI"
author = "Martin Lemay"
copyright = "2026 Martin Lemay"
# single source of truth: pywellsfmui.__version__
_match = re.search(
    r'^__version__ = "([^"]+)"', _INIT.read_text(encoding="utf-8"), re.M
)
if _match is None:
    raise RuntimeError(f"__version__ not found in {_INIT}")
release = _match.group(1)

extensions = [
    "myst_parser",
    "sphinx.ext.intersphinx",
]

intersphinx_mapping = {
    "pywellsfm": ("https://pywellsfm.readthedocs.io/en/latest/", None),
}

myst_enable_extensions = [
    "colon_fence",
    "fieldlist",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "superpowers"]

html_theme = "furo"
html_static_path = ["_static"]
html_title = "pyWellSFMUI"
