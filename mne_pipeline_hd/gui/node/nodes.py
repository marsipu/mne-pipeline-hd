# -*- coding: utf-8 -*-
import logging

from mne_pipeline_hd.gui.gui_utils import get_exception_tuple
from mne_pipeline_hd.gui.node.base_node import BaseNode
from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QDialog,
    QScrollArea,
    QGroupBox,
)

from mne_pipeline_hd.gui.base_widgets import CheckList
from mne_pipeline_hd.gui.loading_widgets import AddFilesWidget, AddMRIWidget
from mne_pipeline_hd.gui import parameter_widgets


class BaseInputNode(BaseNode):
    """Node for input data like MEEG, FSMRI, etc."""

    # Add Start button (Depending from where we start, we get different orders of execution)
    # There can be secondary inputs
    def __init__(self, ct):
        super().__init__(ct)
        self.data_type = None
        self.widget = QWidget()

    def init_widgets(self, data_type):
        self.data_type = data_type
        self.name = f"{data_type} Input Node"
        # Add the output port
        self.add_output("Data", multi_connection=True)
        # Initialize the other widgets inside the node
        layout = QVBoxLayout(self.widget)
        import_bt = QPushButton("Import")
        import_bt.clicked.connect(self.add_files)
        layout.addWidget(import_bt)
        input_list = CheckList(
            # self.ct.inputs[data_type],
            # self.ct.selected_inputs[data_type],
            self.ct.pr.all_meeg,
            self.ct.pr.sel_meeg,
            ui_button_pos="bottom",
            show_index=True,
            title=f"Select {data_type}",
        )
        layout.addWidget(input_list)
        self.add_widget(self.widget)

    def add_files(self):
        # This decides, wether the dialog is rendered outside or inside the scene
        dlg = QDialog(self.viewer)
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


class GroupNode(BaseNode):
    def __init__(self, ct):
        super().__init__(ct, name="Group Node")
        # This node should be adaptive, when a new input data-type is connected,
        # it should change the names of input-ports and output-ports accordingly
        self.add_input("Data-In", multi_connection=True, accepted_ports=None)
        self.add_output("Data-Out", multi_connection=True, accepted_ports=None)

        # ToDo: This will have a widget for selecting and organizing groups


class FunctionNode(BaseNode):
    """This node is a prototype for a function node, which also displays parameters."""

    def __init__(
        self, ct, name, parameters, **kwargs
    ):  # **kwargs just for demo, later not needed
        super().__init__(ct, name, **kwargs)
        self.parameters = parameters

        self.init_parameters()

    def init_parameters(self):
        group_box = QGroupBox("Parameters")
        layout = QVBoxLayout(group_box)
        if len(self.parameters) > 5:
            widget = QScrollArea()
            sub_widget = QWidget()
            layout = QVBoxLayout(sub_widget)
            widget.setWidget(sub_widget)

        for name, param_kwargs in self.parameters.items():
            alias = param_kwargs.get("alias", name)
            gui = param_kwargs.get("gui", None)
            default = param_kwargs.get("default", None)
            if default is None:
                logging.error(f"For parameter {name} no default value was defined.")
                continue
            if gui is None:
                logging.error(f"For parameter {name} no GUI was defined.")
                continue
            extra_kwargs = {
                k: v
                for k, v in param_kwargs.items()
                if k not in ["alias", "gui", "default"]
            }
            try:
                parameter_gui = getattr(parameter_widgets, gui)(
                    data=self.ct,
                    name=name,
                    alias=alias,
                    default=default,
                    **extra_kwargs,
                )
            except Exception:
                err_tuple = get_exception_tuple()
                logging.error(
                    f'Initialization of Parameter-Widget "{name}" '
                    f"with value={default} "
                    f"failed:\n"
                    f"{err_tuple[1]}"
                )
            else:
                layout.addWidget(parameter_gui)
        self.add_widget(group_box)

    def to_dict(self):
        """Override dictionary representation because of additional attributes"""
        node_dict = super().to_dict()
        node_dict["parameters"] = self.parameters

        return node_dict

    def mouseDoubleClickEvent(self, event):
        # Open a dialog to show the code of the function (maybe even small editor)
        pass


class AssignmentNode(BaseNode):
    """This node assigns the input from 1 to an input upstream from 2,
    which then leads to runningo the functions before for input 2 while caching input 1.
    """

    # ToDo:
    # Checks for assignments and if there are pairs for each input.
    # Checks also for inputs in multiple pairs.
    # Status color and status message (like "24/28 assigned")
    # Should change port names depending on data-type connected
    def __init__(self, ct, **kwargs):  # **kwargs just for demo, later not needed
        super().__init__(ct, **kwargs)
        self.name = "Assignment Node"
