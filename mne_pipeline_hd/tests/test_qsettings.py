# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

from qtpy.QtCore import QSettings

from pipeline.pipeline_utils import default_qsettings


def test_qsettings_types(qtbot):
    """Test if QSettings keep types on all operating systems."""

    for v in default_qsettings:
        QSettings().setValue(v, default_qsettings[v])

    for v in default_qsettings:
        value = QSettings().value(v)
        if value is not None:
            assert isinstance(value, type(default_qsettings[v]))
