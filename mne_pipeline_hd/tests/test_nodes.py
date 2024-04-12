# -*- coding: utf-8 -*-
import sys

from PyQt5.QtWidgets import QApplication
from mne_pipeline_hd.gui.node.node_viewer import NodeViewer
from mne_pipeline_hd.gui.node.nodes import MEEGInputNode, FunctionNode, AssignmentNode
from pipeline.controller import NewController


def test_node_graph(qtbot, nodegraph):
    nodegraph.widget.show()
    qtbot.stop()


def run_graph_test():
    app = QApplication(sys.argv)

    ct = NewController()
    viewer = NodeViewer(ct)
    input_node = viewer.create_node(MEEGInputNode)
    func_node = viewer.create_node(FunctionNode)
    ass_node = viewer.create_node(AssignmentNode)

    input_node.set_output(0, func_node.input(0))
    func_node.set_output(0, ass_node.input(0))

    sys.exit(app.exec())


if __name__ == "__main__":
    run_graph_test()
