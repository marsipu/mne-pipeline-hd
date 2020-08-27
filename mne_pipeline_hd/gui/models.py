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
    """ A basic List-Model

    Parameters
    ----------
    data : list of str
        input existing list here, otherwise defaults to empty list

    """

    def __init__(self, data=None):
        super().__init__()
        self._data = data or list()

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            return self._data[index.row()]

    def rowCount(self, index=QModelIndex()):
        return len(self._data)


class EditListModel(BaseListModel):
    """An editable List-Model

    Parameters
    ----------
    data : list of str
        input existing list here, otherwise defaults to empty list

    Notes
    -----
    This model only returns strings, so any value entered will be converted to a string
    """

    def __init__(self, data):
        super().__init__(data)

    def flags(self, index=QModelIndex()):
        return QAbstractItemModel.flags(self, index) | Qt.ItemIsEditable

    def setData(self, index, value, role=None):
        if role == Qt.EditRole:
            self._data[index.row()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def insertRows(self, row, count, index=QModelIndex()):
        self.beginInsertRows(index, row, row + count - 1)
        for pos in range(row, row + count):
            self._data.insert(pos, '')
        self.endInsertRows()
        return True

    def removeRows(self, row, count, index=QModelIndex()):
        self.beginRemoveRows(index, row, row + count - 1)
        for item in [self._data[i] for i in range(row, row + count)]:
            self._data.remove(item)
        self.endRemoveRows()
        return True


class CheckListModel(BaseListModel):
    """
    A Model for a Check-List

    Parameters
    ----------
    data : list
        list with content to be displayed, defaults to empty list

    checked : list
        list which stores the checked items from data

    Notes
    -----
    This model only returns strings, so any value entered will be converted to a string
    """

    def __init__(self, data=None, checked=None):
        super().__init__(data)
        self._data = data or list()
        self._checked = checked or list()

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            return self._data[index.row()]

        if role == Qt.CheckStateRole:
            if self._data[index.row()] in self._checked:
                return Qt.Checked
            else:
                return Qt.Unchecked

    def setData(self, index, value, role=None):
        if role == Qt.CheckStateRole:
            if value == Qt.Checked:
                self._checked.append(self._data[index.row()])
            else:
                self._checked.remove(self._data[index.row()])
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index=QModelIndex()):
        return QAbstractItemModel.flags(self, index) | Qt.ItemIsUserCheckable


class BasePandasModel(QAbstractTableModel):
    """Basic Model for pandas DataFrame

    Parameters
    ----------
    data : pandas.DataFrame | None
        pandas DataFrame with contents to be displayed, defaults to empty DataFrame
    """
    def __init__(self, data=None):
        super().__init__()
        if data is None:
            self._data = pd.DataFrame(np.nan, index=[], columns=[])
        else:
            self._data = data

    def data(self, index, role=None):
        value = self._data.iloc[index.row(), index.column()]

        if role == Qt.DisplayRole:
            return str(value)

    def headerData(self, idx, orientation, role=None):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[idx])
            elif orientation == Qt.Vertical:
                return str(self._data.index[idx])

    def rowCount(self, index=QModelIndex()):
        return len(self._data.index)

    def columnCount(self, index=QModelIndex()):
        return len(self._data.columns)


class EditPandasModel(BasePandasModel):
    """ Editable TableModel for Pandas DataFrames
    Parameters
    ----------
    data : pandas.DataFrame | None
        pandas DataFrame with contents to be displayed, defaults to empty DataFrame

    Notes
    -----
    The reference of the original input-DataFrame is lost when edited by this Model,
    you need to retrieve it directly from the model after editing
    """
    def __init__(self, data=None):
        super().__init__(data)

    def setData(self, index, value, role=None):
        if role == Qt.EditRole:
            try:
                self._data.iloc[index.row(), index.column()] = value
                self.dataChanged.emit(index, index, [role])
                return True

            except ValueError:
                pass

        return False

    def setHeaderData(self, index, orientation, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            if orientation == Qt.Vertical:
                self._data.rename(index={self._data.index[index]: value}, inplace=True)
                self.headerDataChanged.emit(Qt.Vertical, index, index)
                return True

            elif orientation == Qt.Horizontal:
                self._data.rename(columns={self._data.columns[index]: value}, inplace=True)
                self.headerDataChanged.emit(Qt.Horizontal, index, index)
                return True

        return False

    def flags(self, index=QModelIndex()):
        return QAbstractItemModel.flags(self, index) | Qt.ItemIsEditable

    def insertRows(self, row, count, index=QModelIndex()):
        self.beginInsertRows(index, row, row + count - 1)
        add_data = pd.DataFrame(columns=self._data.columns, index=[r for r in range(count)])
        if row == 0:
            self._data = pd.concat([add_data, self._data])
        elif row == len(self._data.index):
            self._data = self._data.append(add_data)
        else:
            self._data = pd.concat([self._data.iloc[:row], add_data, self._data.iloc[row:]])
        self.endInsertRows()

        return True

    def insertColumns(self, column, count, index=QModelIndex()):
        self.beginInsertColumns(index, column, column + count - 1)
        add_data = pd.DataFrame(index=self._data.index, columns=[c for c in range(count)])
        if column == 0:
            self._data = pd.concat([add_data, self._data], axis=1)
        elif column == len(self._data.columns):
            self._data = self._data.join(add_data)
        else:
            self._data = pd.concat([self._data.iloc[:, :column], add_data, self._data.iloc[:, column:]], axis=1)
        self.endInsertColumns()

        return True

    def removeRows(self, row, count, index=QModelIndex()):
        self.beginRemoveRows(index, row, row + count - 1)
        # Can't use DataFrame.drop() here, because there could be rows with similar index-labels
        if row == 0:
            self._data = self._data.iloc[row + count:]
        elif row + count >= len(self._data.index):
            self._data = self._data.iloc[:row]
        else:
            self._data = pd.concat([self._data.iloc[:row], self._data.iloc[row + count:]])
        self.endRemoveRows()

        return True

    def removeColumns(self, column, count, index=QModelIndex()):
        self.beginRemoveColumns(index, column, column + count - 1)
        # Can't use DataFrame.drop() here, because there could be columns with similar column-labels
        if column == 0:
            self._data = self._data.iloc[:, column + count:]
        elif column + count >= len(self._data.columns):
            self._data = self._data.iloc[:, :column]
        else:
            self._data = pd.concat([self._data.iloc[:, :column], self._data.iloc[:, column + count:]], axis=1)
        self.endRemoveColumns()

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
        value = self._data.iloc[index.row(), index.column()]
        column = self._data.columns[index.column()]

        if role == Qt.DisplayRole:
            return value

        if role == Qt.CheckStateRole:
            if column == 'Is Empty-Room?':
                if value:
                    return Qt.Checked
                else:
                    return Qt.Unchecked
