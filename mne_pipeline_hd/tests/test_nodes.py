# -*- coding: utf-8 -*-


def test_node_graph(qtbot, nodegraph):
    nodegraph.widget.show()
    qtbot.stop()
