# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""
from os import mkdir

import pytest

from mne_pipeline_hd.gui.node.node_viewer import NodeViewer
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
def nodeviewer(qtbot):
    viewer = NodeViewer(NewController(), debug_mode=True)
    viewer.resize(1000, 1000)
    qtbot.addWidget(viewer)
    viewer.show()

    func_kwargs = {
        "ports": [
            {
                "name": "In1",
                "port_type": "in",
                "accepted_ports": ["Out1"],
            },
            {
                "name": "In2",
                "port_type": "in",
                "accepted_ports": ["Out1, Out2"],
            },
            {
                "name": "Out1",
                "port_type": "out",
                "accepted_ports": ["In1"],
                "multi_connection": True,
            },
            {
                "name": "Out2",
                "port_type": "out",
                "accepted_ports": ["In1", "In2"],
                "multi_connection": True,
            },
        ],
        "name": "test_func",
        "parameters": {
            "low_cutoff": {
                "alias": "Low-Cutoff",
                "gui": "FloatGui",
                "default": 0.1,
            },
            "high_cutoff": {
                "alias": "High-Cutoff",
                "gui": "FloatGui",
                "default": 0.2,
            },
        },
    }
    func_node1 = viewer.create_node("FunctionNode", **func_kwargs)
    func_node2 = viewer.create_node("FunctionNode", **func_kwargs)
    func_node1.output(port_idx=0).connect_to(func_node2.input(port_idx=0))

    func_node2.setPos(400, 100)

    return viewer
