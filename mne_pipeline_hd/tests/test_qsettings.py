# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""

import json
import sys
from importlib import resources

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication


def test_qsettings_types():
    """Test if QSettings keep types on all operating systems."""
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setApplicationName('test')

    with resources.open_text('mne_pipeline_hd.pipeline_resources',
                             'default_settings.json') as file:
        default_qsettings = json.load(file)['qsettings']

    if len(QSettings().childKeys()) == 0:
        for v in default_qsettings:
            QSettings().setValue(v, default_qsettings[v])
        test_qsettings_types()
        # ToDo: This test as for now is only sensitive after been
        #   run at least twice because in one run the values are
        #   apparently somehow cached. (maybe better with pytest-qt)
        app.quit()
        del app

    for v in default_qsettings:
        value = QSettings().value(v)
        if value is not None:
            assert isinstance(value, type(default_qsettings[v]))
