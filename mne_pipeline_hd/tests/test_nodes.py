# -*- coding: utf-8 -*-
from mne_pipeline_hd.gui.gui_utils import mouseDrag
from qtpy.QtCore import Qt


def test_node_graph(qtbot, nodeviewer):
    node1 = nodeviewer.node(node_idx=0)
    node2 = nodeviewer.node(node_idx=1)

    out2_pos = nodeviewer.port_position_view("out", 1, node_idx=0)
    in2_pos = nodeviewer.port_position_view("in", 1, node_idx=1)
    mouseDrag(
        widget=nodeviewer.viewport(),
        positions=[out2_pos, in2_pos],
        button=Qt.MouseButton.LeftButton,
    )

    assert node1.id in node2.input(1).connected_ports
