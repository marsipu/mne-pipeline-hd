# -*- coding: utf-8 -*-
from gui.node.node_viewer import NodeViewer

from NodeGraphQt import BaseNode


def test_node_graph(qtbot, nodegraph):
    nodegraph.widget.show()
    qtbot.stop()


def run_graph_test():
    nodegraph = NodeViewer()
    nodegraph.add_node(BaseNode)
