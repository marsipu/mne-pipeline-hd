# -*- coding: utf-8 -*-
import sys

from NodeGraphQt.base.factory import NodeFactory
from qtpy.QtWidgets import QApplication, QMainWindow
from NodeGraphQt import (
    BaseNode,
    NodeGraph,
    NodeBaseWidget,
    NodesPaletteWidget,
)

from mne_pipeline_hd.gui.base_widgets import CheckList


class PipeNodeFactory(NodeFactory):
    """This overrrides the NodeFactory to insert a Controller-object
    as an argument to node-creation."""

    def __init__(self, ct):
        self.ct = ct
        super().__init__()

    def create_node_instance(self, node_type=None):
        if node_type in self.aliases:
            node_type = self.aliases[node_type]

        _NodeClass = self.nodes.get(node_type)
        if _NodeClass:
            return _NodeClass(self.ct)


class PipeNodeBaseWidget(NodeBaseWidget):
    """Base class for all node-widgets in the pipeline.
    Since pipeline is not making use of the property system,
    this class makes cicumvention easier."""

    def __init__(self, parent=None, name=None, label=None):
        super().__init__(parent, name, label)

    def get_value(self):
        return

    def set_value(self, value):
        pass


class PipeBaseNode(BaseNode):
    """Base class for all nodes in the pipeline.
    This simplifies some functionality and adds some custom methods.
    """

    __identifier__ = "pipeline_nodes"
    NODE_NAME = "NodeName"

    def __init__(self):
        super().__init__()

    def add_widget(self, widget, widget_type=None, tab=None):
        wrapper_widget = PipeNodeBaseWidget(self.view, "widget_name", "widget_label")
        wrapper_widget.set_custom_widget(widget)
        super().add_custom_widget(wrapper_widget, widget_type, tab=tab)


class InputNode(PipeBaseNode):
    def __init__(self, ct):
        super().__init__()
        meeg_list = CheckList(
            [1, 2, 3],
            [1, 2],
            ui_button_pos="top",
            show_index=True,
            title="Select MEG/EEG",
        )
        self.add_widget(meeg_list, tab="input")

        self.add_output("Data", multi_output=True)


class FunctionNode(BaseNode):
    __identifier__ = "function"
    NODE_NAME = "Function Node"

    def __init__(self, ct):
        super().__init__()

        self.add_input("Data-In 1")
        self.add_input("Data-In 2")

        self.add_output("Data-Out", multi_output=True)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.graph = NodeGraph(node_factory=PipeNodeFactory(self))
        self.setCentralWidget(self.graph.widget)
        self.graph.register_nodes([InputNode, FunctionNode])

        input_node = self.graph.create_node("pipeline_nodes.InputNode")
        func_node = self.graph.create_node("function.FunctionNode")
        func_node2 = self.graph.create_node("function.FunctionNode")

        input_node.set_output(0, func_node.input(0))
        func_node2.set_input(1, func_node.output(0))

        self.graph.auto_layout_nodes()
        self.graph.clear_selection()
        self.graph.fit_to_selection()

        self.nodes_palette = NodesPaletteWidget(parent=None, node_graph=self.graph)
        self.nodes_palette.show()
        self.nodes_palette.setGeometry(200, 200, 300, 200)
        self.resize(1600, 1200)

    def closeEvent(self, event):
        self.nodes_palette.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()

    win.show()
    sys.exit(app.exec())
