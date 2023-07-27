# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

# Keep reference to Qt-objects without parent for tests
# and to avoid garbage collection
_object_refs = {
    "welcome_window": None,
    "main_window": None,
    "plot_manager": None,
    "dialogs": dict(),
    "parameter_widgets": dict(),
}

from mne_pipeline_hd._version import __version__  # noqa
