# -*- coding: utf-8 -*-
from NodeGraphQt import NodeBaseWidget, BaseNode, NodeGraph
from NodeGraphQt.base.factory import NodeFactory

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

    def __init__(self, ct):
        self.ct = ct
        super().__init__()

    def add_widget(self, widget, widget_type=None, tab=None):
        wrapper_widget = PipeNodeBaseWidget(self.view, "widget_name")
        wrapper_widget.set_custom_widget(widget)
        super().add_custom_widget(wrapper_widget, widget_type, tab=tab)


class InputNode(PipeBaseNode):
    def __init__(self, ct):
        super().__init__(ct)
        meeg_list = CheckList(
            ct.pr.all_meeg,
            ct.pr.sel_meeg,
            ui_button_pos="top",
            show_index=True,
            title="Select MEG/EEG",
        )
        self.add_widget(meeg_list, tab="input")

        self.add_output("Data", multi_output=True)


class FunctionNode(PipeBaseNode):
    def __init__(self, ct):
        super().__init__(ct)

        self.add_input("Data-In 1")
        self.add_input("Data-In 2")

        self.add_output("Data-Out", multi_output=True)


class PipeNodeGraph(NodeGraph):
    def __init__(self, ct):
        self.ct = ct
        node_factory = PipeNodeFactory(self.ct)
        super().__init__(node_factory=node_factory)
        self.register_nodes([InputNode, FunctionNode])

        input_node = self.create_node("pipeline_nodes.InputNode")
        func_node = self.create_node("pipeline_nodes.FunctionNode")
        func_node2 = self.create_node("pipeline_nodes.FunctionNode")

        input_node.set_output(0, func_node.input(0))
        func_node2.set_input(1, func_node.output(0))

        self.auto_layout_nodes()
        self.clear_selection()
        self.fit_to_selection()
