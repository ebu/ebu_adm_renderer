# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# add path to ear module for autodoc
import os
import sys

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath(".."))


# -- Project information -----------------------------------------------------

project = "EBU ADM Renderer (EAR)"
copyright = "2021, EBU ADM Renderer Authors"
author = "EBU ADM Renderer Authors"

# The full version, including alpha/beta/rc tags
release = "2.0.0"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx_rtd_theme",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.inheritance_diagram",
    "sphinxarg.ext",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "README.md", "env", "sphinxarg"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

html_theme_options = {
    "navigation_depth": 5,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "lxml": ("https://lxml.de/apidoc", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}


# put parameter / return types in function descriptions
autodoc_typehints = "description"


def autodoc_before_process_signature(app, obj, bound_method):
    # remove return type from __init__ type annotations; these are added by
    # attrs, and while they are true, they don't make any sense in the
    # documentation
    if obj.__name__ == "__init__":
        annotations = getattr(obj, "__annotations__", {})
        if "return" in annotations:
            del annotations["return"]


def setup(app):
    app.connect("autodoc-before-process-signature", autodoc_before_process_signature)

    import importlib

    # list of import-only modules and their contents, which are modified on
    # import to trick sphinx into documenting the in the right place

    alias_modules = {
        "ear.fileio.adm.elements": [
            "AudioBlockFormat",
            "AudioBlockFormatBinaural",
            "AudioBlockFormatDirectSpeakers",
            "AudioBlockFormatHoa",
            "AudioBlockFormatMatrix",
            "AudioBlockFormatObjects",
            "AudioChannelFormat",
            "AudioContent",
            "AudioObject",
            "AudioPackFormat",
            "AudioProgramme",
            "AudioStreamFormat",
            "AudioTrackFormat",
            "AudioTrackUID",
            "BoundCoordinate",
            "CartesianZone",
            "ChannelLock",
            "DirectSpeakerCartesianPosition",
            "DirectSpeakerPolarPosition",
            "DirectSpeakerPosition",
            "FormatDefinition",
            "Frequency",
            "JumpPosition",
            "LoudnessMetadata",
            "MatrixCoefficient",
            "ObjectCartesianPosition",
            "ObjectDivergence",
            "ObjectPolarPosition",
            "ObjectPosition",
            "PolarZone",
            "ScreenEdgeLock",
            "TypeDefinition",
        ],
        "ear.fileio": [
            "openBw64",
            "openBw64Adm",
        ],
        "ear.core.select_items": [
            "select_rendering_items",
        ],
        "ear.core.geom": [
            "cart",
            "azimuth",
            "elevation",
            "distance",
        ],
    }

    for modname, aliases in alias_modules.items():
        mod = importlib.import_module(modname)

        for attr_name in aliases:
            getattr(mod, attr_name).__module__ = modname
