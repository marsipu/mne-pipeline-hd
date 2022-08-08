# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne-pipeline-hd
License: GPL-3.0
"""

import pytest

from mne_pipeline_hd.gui.main_window import MainWindow
from mne_pipeline_hd.pipeline.controller import Controller
from mne_pipeline_hd.pipeline.pipeline_utils import _set_test_run


@pytest.fixture
def controller(tmpdir):
    _set_test_run()
    ct = Controller(tmpdir, 'test')

    return ct


@pytest.fixture
def main_window(controller, qtbot):
    mw = MainWindow(controller)
    qtbot.addWidget(mw)

    return mw
