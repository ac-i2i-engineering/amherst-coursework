# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Access Amherst"
copyright = "2024, Dhyey Mavani, Liam Davis, Ryan Ji, Shreya Hegde, Thu Hoang"
author = "Dhyey Mavani, Liam Davis, Ryan Ji, Shreya Hegde, Thu Hoang"
release = "0.0.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    'sphinx.ext.napoleon',
]

templates_path = ["_templates"]
exclude_patterns = []

language = "python"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

extensions.append("sphinx_wagtail_theme")
html_theme = "sphinx_wagtail_theme"
html_theme_options = dict(
    project_name = "Access Amherst",
    logo = "",
    logo_alt = "",
    logo_height = 50,
    logo_url = "/",
    logo_width = 50,
    github_url = "https://github.com/ac-i2i-engineering/access-amherst/",
)

html_static_path = ["_static"]
html_css_files = [
    'custom.css',
]

templates_path = ["_templates"]

# set up Django environment
import os
import sys
import django

sys.path.insert(0, os.path.abspath("../../access_amherst_backend"))
os.environ["DJANGO_SETTINGS_MODULE"] = "access_amherst_backend.settings"
django.setup()
