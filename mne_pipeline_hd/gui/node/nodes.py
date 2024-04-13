# -*- coding: utf-8 -*-
from gui.node.base_node import BaseNode
from qtpy.QtWidgets import QWidget, QVBoxLayout, QPushButton, QDialog

from mne_pipeline_hd.gui.base_widgets import CheckList
from mne_pipeline_hd.gui.loading_widgets import AddFilesWidget, AddMRIWidget


class BaseInputNode(BaseNode):
    """Node for input data like MEEG, FSMRI, etc."""

    # ToDo: Add import functionality.
    # Add Start button (Depending from where we start, we get different orders of execution)
    # There can be secondary inputs
    def __init__(self, ct):
        self.data_type = None
        self.widget = QWidget()
        super().__init__(ct)

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
            self.ct.inputs[data_type],
            self.ct.selected_inputs[data_type],
            ui_button_pos="bottom",
            show_index=True,
            title=f"Select {data_type}",
        )
        layout.addWidget(input_list)
        self.add_widget(self.widget)

    def add_files(self):
        # This decides, wether the dialog is rendered outside or inside the scene
        dlg = QDialog(self.scene().viewer())
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


class FunctionNode(BaseNode):
    def __init__(self, ct):
        super().__init__(ct, name="Function Node")

        self.add_input("In 1", accepted_ports=["Out 1"])
        self.add_input("In 2", accepted_ports=["Out 1", "Out 2"])
        self.add_output("Out 1", multi_connection=True, accepted_ports=["In 1", "In 2"])
        self.add_output("Out 2", multi_connection=True, accepted_ports=["In 2"])


class AssignmentNode(BaseNode):
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

        self.add_input("Data-In 1", multi_connection=False)
        self.add_input("Data-In 2", multi_connection=False)

        self.add_output("Data-Out 1", multi_connection=False)
        self.add_output("Data-Out 2", multi_connection=False)
