import sys
from inspect import getsourcefile
from os.path import abspath
from pathlib import Path

from PyQt5.QtCore import QAbstractTableModel, QTimer, Qt
from PyQt5.QtWidgets import QApplication, QPushButton, QTableView, QVBoxLayout, QWidget

import pandas as pd

package_parent = str(Path(abspath(getsourcefile(lambda: 0))).parent.parent.parent)
sys.path.insert(0, package_parent)

from mne_pipeline_hd.gui.qt_models import (BaseListModel, EditListModel, CheckListModel, BasePandasModel,
                                           EditPandasModel, FileDictModel)


class ModelTest(QWidget):
    def __init__(self):
        super().__init__()

        self.exlist = [1, 2, 3, 'asdf', 3.3423, 'ff']
        self.exchecked = []
        self.expd = pd.DataFrame([[1, 2, 3, 4], [5, 6, 7, 8]],
                                 columns=['File-Name', 'File-Type', 'Is Empty-Room?', 'Path'])
        self.extree = {'Huga': {'mufi': [1, 2, 3, 4],
                                'tufi': ['df', 24],
                                'simba':
                                    {'Af': 234,
                                     'sdf': 44}},
                       'wungi': 8}

        self.model_dict =  {'BaseListModel': self.exlist,
                            'EditListModel': self.exlist,
                            'CheckListModel': self.exlist,
                            'BasePandasModel': BasePandasModel}

        self.init_ui()
        self.show()

    def init_ui(self):
        self.layout = QVBoxLayout()

        self.table_view = QTableView()
        self.table_model = PandasTableModel(self.pd_data)
        self.table_view.setModel(self.table_model)
        self.layout.addWidget(self.table_view)

        self.add_bt = QPushButton('Add')
        self.add_bt.clicked.connect(self.add_row)
        self.layout.addWidget(self.add_bt)

        self.remove_bt = QPushButton('Remove')
        self.remove_bt.clicked.connect(self.remove_row)
        self.layout.addWidget(self.remove_bt)

        self.setLayout(self.layout)

    def add_row(self):
        selection = self.table_model.selectionModel()
        self.table_model.layoutChanged.emit()

    def remove_row(self):
        row_idxs = self.table_view.selectionModel().selectedRows(0)
        for row_idx in row_idxs:
            self.table_model.removeRow(row_idx.row())


# Command-Line interrupt with Ctrl+C possible
timer = QTimer()
timer.timeout.connect(lambda: None)
timer.start(500)

app = QApplication(sys.argv)
testw = PandasModelTest()
sys.exit(app.exec())
