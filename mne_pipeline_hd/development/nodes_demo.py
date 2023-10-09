# -*- coding: utf-8 -*-
import sys

from qtpy.QtWidgets import QApplication, QMainWindow
from NodeGraphQt import (
    BaseNode,
    NodeGraph,
    NodeBaseWidget,
    NodesPaletteWidget,
)

from mne_pipeline_hd.gui.base_widgets import CheckList


class InputWidgetWrapper(NodeBaseWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.set_name("input")
        self.set_label("Select Input-Data")
        self.set_custom_widget(CheckList(["data1", "data2", "data3"]))

    def get_value(self):
        return 1

    def set_value(self, value):
        pass


class InputNode(BaseNode):
    __identifier__ = "input"
    NODE_NAME = "Input Node"

    def __init__(self):
        super().__init__()

        self.input_widget = InputWidgetWrapper(self.view)
        self.add_custom_widget(self.input_widget, tab="input")

        self.add_output("Data", multi_output=True)


class FunctionNode(BaseNode):
    __identifier__ = "function"
    NODE_NAME = "Function Node"

    def __init__(self):
        super().__init__()

        self.add_input("Data-In 1")
        self.add_input("Data-In 2")

        self.add_output("Data-Out", multi_output=True)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.graph = NodeGraph()
        self.setCentralWidget(self.graph.widget)
        self.graph.register_nodes([InputNode, FunctionNode])

        input_node = self.graph.create_node("input.InputNode")
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
