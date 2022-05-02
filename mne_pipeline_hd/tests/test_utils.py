# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""

from PyQt5.QtWidgets import QWidget

from ..gui.main_window import MainWindow
from ..pipeline_functions.controller import Controller


def init_test_instance(tmpdir):
    ct = Controller(tmpdir)
    ct.change_project('Test')

    main_window = MainWindow(ct)
