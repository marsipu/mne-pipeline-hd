# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
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
