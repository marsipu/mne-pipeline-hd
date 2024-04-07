# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""
from os import mkdir

import pytest
from gui.nodes import PipeNodeGraph

from mne_pipeline_hd.gui.main_window import MainWindow
from mne_pipeline_hd.pipeline.controller import Controller, NewController
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


@pytest.fixture
def nodegraph(qtbot):
    node_graph = PipeNodeGraph(NewController())
    qtbot.addWidget(node_graph.widget)

    return node_graph
