# -*- coding: utf-8 -*-
from mne_pipeline_hd.gui.gui_utils import mouseDrag
from qtpy.QtCore import Qt, QPointF


def test_nodes_basic_interaction(nodeviewer):
    node1 = nodeviewer.node(node_idx=0)
    node2 = nodeviewer.node(node_idx=1)

    out1_pos = nodeviewer.port_position_view(port_type="out", port_idx=1, node_idx=0)
    in2_pos = nodeviewer.port_position_view(port_type="in", port_idx=1, node_idx=1)
    mouseDrag(
        widget=nodeviewer.viewport(),
        positions=[out1_pos, in2_pos],
        button=Qt.MouseButton.LeftButton,
    )
    # Check if new connection was created
    assert node1.output(port_idx=1) in node2.input(port_idx=1).connected_ports

    # Slice both connections
    start_slice_pos = QPointF(nodeviewer.mapFromScene(QPointF(200, 180)))
    end_slice_pos = QPointF(nodeviewer.mapFromScene(QPointF(320, 0)))

    mouseDrag(
        widget=nodeviewer.viewport(),
        positions=[start_slice_pos, end_slice_pos],
        button=Qt.MouseButton.LeftButton,
        modifier=Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier,
    )
    # Check if connection was sliced
    assert len(node1.output(port_idx=1).connected_ports) == 0


# ToDo: Finish test
def test_node_serialization(qtbot, nodeviewer):
    viewer_dict = nodeviewer.to_dict()
    qtbot.wait(1000)
    nodeviewer.clear()
    qtbot.wait(1000)
    nodeviewer.from_dict(viewer_dict)
    second_viewer_dict = nodeviewer.to_dict()
    qtbot.wait(10000)
    assert viewer_dict == second_viewer_dict
