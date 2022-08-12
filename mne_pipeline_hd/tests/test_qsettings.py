# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""

import json
from importlib import resources

from PyQt5.QtCore import QSettings


def test_qsettings_types(qtbot):
    """Test if QSettings keep types on all operating systems."""
    with resources.open_text('mne_pipeline_hd.resource',
                             'default_settings.json') as file:
        default_qsettings = json.load(file)['qsettings']

    for v in default_qsettings:
        QSettings().setValue(v, default_qsettings[v])

    for v in default_qsettings:
        value = QSettings().value(v)
        if value is not None:
            assert isinstance(value, type(default_qsettings[v]))
