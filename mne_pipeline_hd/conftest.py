# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
import pytest

from .gui.main_window import MainWindow
from .pipeline_functions.controller import Controller


@pytest.fixture
def main_window(tmpdir, qtbot):
    ct = Controller(tmpdir)
    ct.change_project('Test')

    mw = MainWindow(ct)
    qtbot.addWidget(mw)

    return mw
