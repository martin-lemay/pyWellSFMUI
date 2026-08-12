"""Sphinx configuration for pyWellSFMUI documentation."""

project = "pyWellSFMUI"
author = "Martin Lemay"
release = "0.1.0"

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
