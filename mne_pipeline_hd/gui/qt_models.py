# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
inspired by: https://doi.org/10.3389/fnins.2018.00006
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
from PyQt5.QtCore import QAbstractItemModel, QAbstractListModel, QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtGui import QColor, QFont

import pandas as pd
import numpy as np


class BaseListModel(QAbstractListModel):
    """
    A basic List-Model

    Parameters
    ----------
    data : list of str
        contains list-values, defaults to empty list

    Attributes
    ----------
    _data : list of str
        internal reference to list of strings
    """

    def __init__(self, data=None):
        super().__init__()
        self._data = data or list()

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            return self._data[index.row()]

    def rowCount(self, index=None):
        return len(self._data)


class EditListModel(BaseListModel):
    """An editable List-Model"""

    def __init__(self, data):
        super().__init__(data)

    def flags(self, index=None):
        return QAbstractItemModel.flags(self, index) | Qt.ItemIsEditable

    def setData(self, index, value, role=None):
        if role == Qt.EditRole:
            self._data[index.row()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def insertRows(self, row, count, index=None):
        self.beginInsertRows(index, row, row + count - 1)
        for pos in range(row, count):
            self._data.insert(pos, '')
        self.endInsertRows()
        return True

    def removeRows(self, row, count, index=None):
        self.beginRemoveRows(index, row, row + count - 1)
        for pos in range(row, count):
            self._data.remove(pos)
        self.endRemoveRows()
        return True


class CheckListModel(BaseListModel):
    """
    A Model for a Check-List

    Attributes
    ----------
    _data : list of str
        contains list-values, defaults to empty list

    _checked : list of str
        contains checked values from list

    """

    def __init__(self, data=None, checked=None):
        super().__init__(data)
        self._data = data or list()
        self._checked = checked or list()

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            return self._data[index.row()]

        if role == Qt.CheckStateRole:
            if index.data(Qt.DisplayRole) in self._checked:
                return Qt.Checked
            else:
                return Qt.Unchecked

    def setData(self, index, value, role=None):
        if role == Qt.CheckStateRole:
            if value == Qt.Checked:
                self._checked.append(index.data(Qt.DisplayRole))
            else:
                self._checked.remove(index.data(Qt.DisplayRole))
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index=None):
        return QAbstractItemModel.flags(self, index) | Qt.ItemIsUserCheckable


class BasePandasModel(QAbstractTableModel):
    def __init__(self, pd_data=None):
        super().__init__()
        self.pd_data = pd_data

    def data(self, index, role=None):
        value = self.pd_data.iloc[index.row(), index.column()]

        if role == Qt.DisplayRole:
            return value

    def headerData(self, idx, orientation, role=None):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self.pd_data.columns[idx])
            if orientation == Qt.Vertical:
                return str(self.pd_data.index[idx])

    def rowCount(self, index=None):
        return len(self.pd_data.index)

    def columnCount(self, index=None):
        return len(self.pd_data.columns)


class EditPandasModel(BasePandasModel):
    """
    Editable TableModel for Pandas-DataFrames
    """
    def __init__(self, pd_data=None):
        """
        :param pd_data: The data of the model.
        important: pd_data is rereferenced internally!!!
        So either subclass and set pd_data to an objects reference or retrieve pd_data from model directly
        """
        super().__init__(pd_data)
        self.pd_data = pd_data or pd.DataFrame([])

    def setData(self, index, value, role=None):
        if role == Qt.EditRole:
            try:
                self.pd_data.iloc[index.row(), index.column()] = value
                self.dataChanged.emit(index, index, [role])
                return True

            except ValueError:
                pass

        return False

    def flags(self, index=None):
        return QAbstractItemModel.flags(self, index) | Qt.ItemIsEditable

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
        self.pd_data.drop(index=[r for r in range(count)], inplace=True)
        self.endRemoveRows()

        return True

    def removeColumns(self, column, count, index=None):
        self.beginRemoveColumns(index, column, column + count - 1)
        self.pd_data.drop(columns=[c for c in range(count)], inplace=True)
        self.endRemoveRows()

        return True


class FileDictModel(BaseListModel):
    def __init__(self, data, file_dict):
        super().__init__(data)
        self._data = data
        self.file_dict = file_dict

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            return self._data[index.row()]

        elif role == Qt.FontRole:
            if self._data[index.row()] in self.file_dict:
                pass


class AddFilesModel(BasePandasModel):
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
