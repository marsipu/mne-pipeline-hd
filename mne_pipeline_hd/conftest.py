# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""
from os import mkdir

import pytest
from mne_pipeline_hd.gui.nodes import PipeNodeGraph

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

    input_node1 = node_graph.create_node("pipeline_nodes.MEEGInputNode")
    func_node1 = node_graph.create_node("pipeline_nodes.FunctionNode")
    func_node2 = node_graph.create_node("pipeline_nodes.FunctionNode")
    input_node1.set_output(0, func_node1.input(0))
    func_node1.set_output(0, func_node2.input(0))

    input_node2 = node_graph.create_node("pipeline_nodes.MRIInputNode")
    func_node3 = node_graph.create_node("pipeline_nodes.FunctionNode")
    func_node4 = node_graph.create_node("pipeline_nodes.FunctionNode")
    input_node2.set_output(0, func_node3.input(0))
    func_node3.set_output(0, func_node4.input(0))

    ass_node = node_graph.create_node("pipeline_nodes.AssignmentNode")
    ass_node.set_input(0, func_node2.output(0))
    ass_node.set_input(1, func_node4.output(0))
    func_node5 = node_graph.create_node("pipeline_nodes.FunctionNode")
    ass_node.set_output(0, func_node5.input(0))

    node_graph.auto_layout_nodes()
    node_graph.clear_selection()
    node_graph.fit_to_selection()

    return node_graph
