# -*- coding: utf-8 -*-
import logging
import sys

from PyQt5.QtWidgets import QApplication
from mne_pipeline_hd.gui.node.node_viewer import NodeViewer
from pipeline.controller import NewController


def run_graph_test():
    app = QApplication(sys.argv)

    logging.getLogger().setLevel(logging.DEBUG)

    ct = NewController()
    viewer = NodeViewer(ct)
    viewer.resize(1600, 1000)

    meeg_node = viewer.create_node("MEEGInputNode")
    mri_node = viewer.create_node("MRIInputNode")
    ass_node = viewer.create_node("AssignmentNode")
    func_node1 = viewer.create_node("FunctionNode")
    func_node2 = viewer.create_node("FunctionNode")
    func_node3 = viewer.create_node("FunctionNode")
    func_node4 = viewer.create_node("FunctionNode")

    # Wire up the nodes
    meeg_node.set_output(0, func_node1.input(0))
    func_node1.set_output(0, func_node2.input(0))
    mri_node.set_output(0, func_node3.input(1))
    func_node3.set_output(0, func_node4.input(1))
    ass_node.set_input(0, func_node2.output(0))
    ass_node.set_input(1, func_node4.output(1))

    viewer.show()
    viewer.auto_layout_nodes()
    viewer.clear_selection()
    viewer.fit_to_selection()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_graph_test()
