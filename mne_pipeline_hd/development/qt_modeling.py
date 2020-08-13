import sys

from PyQt5.QtCore import QAbstractTableModel, QTimer, Qt
from PyQt5.QtWidgets import QApplication, QPushButton, QTableView, QVBoxLayout, QWidget

import pandas as pd


class PandasTableModel(QAbstractTableModel):
    """
    Base TableModel for Pandas-DataFrames
    """
    def __init__(self, pd_data=None):
        """
        :param pd_data: The data of the model.
        important: data is rereferenced internally!!!
        So either subclass and change data to change an objects reference or take data from model directly
        """
        super().__init__()
        self.pd_data = pd_data or pd.DataFrame([])

    def data(self, index, role=None):
        value = self.pd_data.iloc[index.row(), index.column()]

        if role == Qt.DisplayRole:
            return value

    def setData(self, index, value, role=None):
        if role == Qt.EditRole:
            try:
                self.pd_data.iloc[index.row(), index.column()] = value
                self.dataChanged.emit(index, index, [role])
                return True

            except ValueError:
                return False

        return False

    def flags(self, index=None):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

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

    def insertRows(self, row, count, index=None):
        self.beginInsertRows(index, row, row + count - 1)
        add_data = pd.DataFrame(np.nan, index=[r for r in range(row, count)],
                                columns=self.pd_data.columns)
        if row == 0:
            self.pd_data = pd.concat([add_data, self.pd_data])
        elif row == len(self.pd_data.index):
            self.pd_data = self.pd_data.append(add_data)
        else:
            self.pd_data = pd.concat([self.pd_data.iloc[:row], add_data, self.pd_data.iloc[row:]])
        self.endInsertRows()

        return True

    def insertColumns(self, column, count, index=None):
        self.beginInsertColumns(index, column, column + count - 1)
        add_data = pd.DataFrame(np.nan, index=self.pd_data.index,
                                columns=[c for c in range(column, count)])
        if column == 0:
            self.pd_data = pd.concat([add_data, self.pd_data], axis=1)
        elif column == len(self.pd_data.columns):
            for column in add_data.columns:
                self.pd_data[column] = add_data[column]
        else:
            self.pd_data = pd.concat([self.pd_data[:column], add_data, self.pd_data[column:]], axis=1)
        self.endInsertColumns()

        return True

    def removeRows(self, row, count, index=None):
        self.beginRemoveRows(index, row, row + count - 1)
        for _ in range(count):
            self.pd_data.drop(index=row, inplace=True)
        self.endRemoveRows()

        return True

    def removeColumns(self, column, count, index=None):
        self.beginRemoveColumns(index, column, column + count - 1)
        for _ in range(count):
            self.pd_data.drop(column=column, inplace=True)
        self.endRemoveRows()

        return True


class PandasModelTest(QWidget):
    def __init__(self):
        super().__init__()

        self.pd_data = pd.DataFrame([[1, 2, 3, 4]], columns=['File-Name', 'File-Type', 'Is Empty-Room?', 'Path'])

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
