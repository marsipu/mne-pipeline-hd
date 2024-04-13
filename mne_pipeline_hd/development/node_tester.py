# -*- coding: utf-8 -*-
import logging
import sys

from PyQt5.QtWidgets import QApplication
from mne_pipeline_hd.gui.node.node_viewer import NodeViewer
from mne_pipeline_hd.gui.node.nodes import FunctionNode
from pipeline.controller import NewController


def run_graph_test():
    app = QApplication(sys.argv)

    logging.getLogger().setLevel(logging.DEBUG)

    ct = NewController()
    viewer = NodeViewer(ct)
    viewer.resize(1000, 1000)
    # input_node = viewer.create_node(MEEGInputNode)
    # ass_node = viewer.create_node(AssignmentNode)
    #
    # input_node.set_output(0, func_node.input(0))

    func_node1 = viewer.create_node(FunctionNode)
    func_node2 = viewer.create_node(FunctionNode)
    func_node1.set_output(0, func_node2.input(0))

    func_node2.setPos(400, 100)

    viewer.show()
    viewer.auto_layout_nodes()
    viewer.clear_selection()
    viewer.fit_to_selection()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_graph_test()
