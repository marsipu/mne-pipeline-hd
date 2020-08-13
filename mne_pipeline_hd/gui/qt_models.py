# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
inspired by: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
from PyQt5.QtCore import QAbstractListModel, QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtGui import QColor, QFont

import pandas as pd
import numpy as np

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


