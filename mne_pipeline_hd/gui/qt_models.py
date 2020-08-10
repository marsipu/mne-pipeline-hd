# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
inspired by: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
from PyQt5.QtCore import QAbstractListModel, QAbstractTableModel, Qt
from PyQt5.QtGui import QColor, QFont


class CheckListModel(QAbstractListModel):
    def __init__(self, data=None, checked=None):
        super().__init__()
        self._data = data
        self._checked = checked

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            return self._data[index.row()]

        if role == Qt.CheckStateRole:
            if index.data(Qt.DisplayRole) in self._checked:
                return Qt.Checked
            else:
                return Qt.Unchecked

    def setData(self, index, value, role=None):
        if index.isValid() and role != Qt.CheckStateRole:
            return False

        if role == Qt.CheckStateRole:
            if value == Qt.Checked:
                self._checked.append(index.data(Qt.DisplayRole))
            else:
                self._checked.remove(index.data(Qt.DisplayRole))

        self.dataChanged.emit(index, index)
        return True

    def rowCount(self, index=None):
        return len(self._data)

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable


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
        value = self.pd_data.iloc[index.row(), index.column()]
        column = self.pd_data.columns[index.column()]

        if role == Qt.DisplayRole:
            return value

        if role == Qt.CheckStateRole:
            if column == 'Is Empty-Room?':
                if value:
                    return Qt.Checked
                else:
                    return Qt.Unchecked


