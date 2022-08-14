# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""
# Keep reference to Qt-objects without parent for tests
# and to avoid garbage collection
_object_refs = {'welcome_window': None,
                'main_window': None,
                'plot_manager': None,
                'dialogs': dict(),
                'parameter_widgets': dict()}

from mne_pipeline_hd._version import __version__  # noqa
