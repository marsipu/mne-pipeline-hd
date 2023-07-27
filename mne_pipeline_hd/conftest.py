# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""
from os import mkdir

import pytest

from mne_pipeline_hd.gui.main_window import MainWindow
from mne_pipeline_hd.pipeline.controller import Controller
from mne_pipeline_hd.pipeline.pipeline_utils import _set_test_run


@pytest.fixture
def controller(tmpdir):
    # Initialize testing-environment
    _set_test_run()
    # Create home-path
    home_path = tmpdir.join("TestHome")
    mkdir(home_path)
    # Create Controller
    ct = Controller(home_path, "test")

    return ct


@pytest.fixture
def main_window(controller, qtbot):
    mw = MainWindow(controller)
    qtbot.addWidget(mw)

    return mw
