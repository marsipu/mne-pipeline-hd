# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
Written on top of MNE-Python
Copyright © 2011-2021, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
"""
import time
import pytest

from mne_pipeline_hd.gui.gui_utils import WorkerDialog


@pytest.fixture
def test_blocking_worker_dialog(qtbot):
    def _test_func():
        time.sleep(2)

    time1 = time.time()
    worker_dlg = WorkerDialog(qtbot, _test_func)
    qtbot.addWidget(worker_dlg)
    time2 = time.time()

    assert time2 - time1 > 1


if __name__ == '__main__':
    test_blocking_worker_dialog()
