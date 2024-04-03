# Configuration file for the Sphinx documentation builder.

# -- Path setup --------------------------------------------------------------

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

import pe


# -- Project information -----------------------------------------------------

project = 'PyHam PE'
copyright = '2024, Martin F N Cooper. All rights reserved'
author = 'Martin F N Cooper'
release = pe.__version__
version = release


# -- General configuration ---------------------------------------------------

extensions = [
    'autoapi.extension'
]
autoapi_dirs = ['../pe']
autoapi_options = [
    'members',
    'show-inheritance',
    'show-module-summary',
    'imported-members'
]

templates_path = ['_templates']

rst_prolog = """
.. meta::
   :author: Martin F N Cooper
   :description: A client implementation of the AGWPE protocol, providing a
      simple means of communicating with an AGWPE server via TCP/IP.
"""


# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'prev_next_buttons_location': 'none'
}
html_show_sourcelink = False
