import sys

from PyQt5.QtCore import QAbstractTableModel, QTimer, Qt
from PyQt5.QtWidgets import QApplication, QPushButton, QTableView, QVBoxLayout, QWidget

import pandas as pd


class PandasTableModel(QAbstractTableModel):
    def __init__(self, pd_data):
        super().__init__()
        self.pd_data = pd_data

    def data(self, index, role=None):
        value = self.pd_data.iloc[index.row(), index.column()]

        if role == Qt.DisplayRole:
            return value

    def rowCount(self, index=None):
        return len(self.pd_data.index)

    def columnCount(self, index=None):
        return len(self.pd_data.columns)

    def headerData(self, idx, orientation, role=None):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self.pd_data.columns[idx])
            if orientation == Qt.Vertical:
                return str(self.pd_data.index[idx])


class AddFilesModel(PandasTableModel):
    def __init__(self, pd_data):
        super().__init__(pd_data)

    def data(self, index, role=None):
        value = str(self.pd_data.iloc[index.row(), index.column()])
        column = self.pd_data.columns[index.column()]

        if role == Qt.DisplayRole:
            return value

        if role == Qt.CheckStateRole:
            if column == 'Is Empty-Room?':
                if value:
                    return Qt.Checked
                else:
                    return Qt.Unchecked

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def setData(self, index, value, role=None):
        if role == Qt.EditRole:
            self.pd_data.iloc[index.row(), index.column()] = value
            self.dataChanged.emit()

            return True

        return False


class EditableTableTest(QWidget):
    def __init__(self):
        super().__init__()

        self.pd_data = pd.DataFrame([[1, 2, 3, 4]], columns=['File-Name', 'File-Type', 'Is Empty-Room?', 'Path'])

        self.init_ui()
        self.show()

    def init_ui(self):
        self.layout = QVBoxLayout()

        self.table_view = QTableView()
        self.table_model = AddFilesModel(self.pd_data)
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
        self.pd_data = self.pd_data.append(pd.Series([1, 2, 3, 4], index=self.pd_data.columns), ignore_index=True)
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
testw = EditableTableTest()
sys.exit(app.exec())
