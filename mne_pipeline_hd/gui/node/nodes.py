# -*- coding: utf-8 -*-
from qtpy.QtWidgets import QWidget, QVBoxLayout, QPushButton, QDialog

from NodeGraphQt import NodeBaseWidget, BaseNode, NodeGraph
from NodeGraphQt.base.factory import NodeFactory

from mne_pipeline_hd.gui.base_widgets import CheckList
from mne_pipeline_hd.gui.loading_widgets import AddFilesWidget, AddMRIWidget


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

    def __init__(self, ct):
        self.ct = ct
        super().__init__()

    def add_widget(self, widget, widget_type=None, tab=None):
        wrapper_widget = PipeNodeBaseWidget(self.view, "widget_name")
        wrapper_widget.set_custom_widget(widget)
        super().add_custom_widget(wrapper_widget, widget_type, tab=tab)


class BaseInputNode(PipeBaseNode):
    """Node for input data like MEEG, FSMRI, etc."""

    # ToDo: Add import functionality.
    # Add Start button (Depending from where we start, we get different orders of execution)
    # There can be secondary inputs
    def __init__(self, ct):
        self.NODE_NAME = "Input Data"
        self.data_type = None
        super().__init__(ct)

    def init_widgets(self, data_type):
        self.data_type = data_type
        # Add the output port
        self.add_output("Data", multi_output=True)
        # Initialize the other widgets inside the node
        node_widget = QWidget()
        layout = QVBoxLayout(node_widget)
        import_bt = QPushButton("Import")
        import_bt.clicked.connect(self.add_files)
        layout.addWidget(import_bt)
        input_list = CheckList(
            self.ct.inputs[data_type],
            self.ct.selected_inputs[data_type],
            ui_button_pos="bottom",
            show_index=True,
            title=f"Select {data_type}",
        )
        layout.addWidget(input_list)
        self.add_widget(node_widget)

    def add_files(self):
        dlg = QDialog(self.graph.widget)
        dlg.setWindowTitle("Import Files")
        if self.data_type == "MEEG":
            widget = AddFilesWidget(self.ct)
        else:
            widget = AddMRIWidget(self.ct)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.addWidget(widget)
        dlg.open()


class MEEGInputNode(BaseInputNode):
    def __init__(self, ct):
        super().__init__(ct)
        self.init_widgets("MEEG")


class MRIInputNode(BaseInputNode):
    def __init__(self, ct):
        super().__init__(ct)
        self.init_widgets("FSMRI")


class FunctionNode(PipeBaseNode):
    def __init__(self, ct):
        self.NODE_NAME = "Function Node"
        super().__init__(ct)

        self.add_input("Data-In")

        self.add_output("Data-Out", multi_output=True)


class AssignmentNode(PipeBaseNode):
    """This node assigns the input from 1 to an input upstream from 2,
    which then leads to runningo the functions before for input 2 while caching input 1.
    """

    # ToDo:
    # Checks for assignments and if there are pairs for each input.
    # Checks also for inputs in multiple pairs.
    # Status color and status message (like "24/28 assigned")
    def __init__(self, ct):
        self.NODE_NAME = "Assignment Node"
        super().__init__(ct)

        self.add_input("Data-In 1", multi_input=False)
        self.add_input("Data-In 2", multi_input=False)

        self.add_output("Data-Out 1", multi_output=False)
        self.add_output("Data-Out 2", multi_output=False)


class PipeNodeGraph(NodeGraph):
    def __init__(self, ct):
        self.ct = ct
        node_factory = PipeNodeFactory(self.ct)
        super().__init__(node_factory=node_factory)
        self.register_nodes([MEEGInputNode, MRIInputNode, AssignmentNode, FunctionNode])
