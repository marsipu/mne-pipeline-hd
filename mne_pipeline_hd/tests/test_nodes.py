# -*- coding: utf-8 -*-
from mne_pipeline_hd.gui.gui_utils import mouseDrag
from qtpy.QtCore import Qt, QPointF


def test_nodes_basic_interaction(qtbot, nodeviewer):
    node1 = nodeviewer.node(node_idx=0)
    node2 = nodeviewer.node(node_idx=1)

    out2_pos = nodeviewer.port_position_view("out", 1, node_idx=0)
    in2_pos = nodeviewer.port_position_view("in", 1, node_idx=1)
    mouseDrag(
        widget=nodeviewer.viewport(),
        positions=[out2_pos, in2_pos],
        button=Qt.MouseButton.LeftButton,
    )
    # Check if new connection was created
    assert node1.id in node2.input(1).connected_ports

    # Slice both connections
    start_slice_pos = nodeviewer.mapFromScene(QPointF(200, 180))
    end_slice_pos = nodeviewer.mapFromScene(QPointF(320, 0))

    mouseDrag(
        widget=nodeviewer.viewport(),
        positions=[start_slice_pos, end_slice_pos],
        button=Qt.MouseButton.LeftButton,
        modifier=Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier,
    )
    # Check if connection was sliced
    assert len(node1.output(1).connected_ports) == 0
