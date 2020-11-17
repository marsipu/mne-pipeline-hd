# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
Copyright © 2011-2019, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
"""
from ast import literal_eval

import pandas as pd
from PyQt5.QtCore import QAbstractItemModel, QAbstractListModel, QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtGui import QBrush, QFont
from PyQt5.QtWidgets import QApplication, QStyle


class BaseListModel(QAbstractListModel):
    """ A basic List-Model

    Parameters
    ----------
    data : list()
        input existing list here, otherwise defaults to empty list

    """

    def __init__(self, data=None):
        super().__init__()
        if data is None:
            self._data = list()
        else:
            self._data = data

    def getData(self, index=QModelIndex()):
        return self._data[index.row()]

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            return str(self.getData(index))

    def rowCount(self, index=QModelIndex()):
        return len(self._data)


class EditListModel(BaseListModel):
    """An editable List-Model

    Parameters
    ----------
    data : list()
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
            try:
                self._data[index.row()] = literal_eval(value)
            except (ValueError, SyntaxError):
                self._data[index.row()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def insertRows(self, row, count, index=QModelIndex()):
        self.beginInsertRows(index, row, row + count - 1)
        for pos in range(row, row + count):
            self._data.insert(pos, '__new__')
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
    data : list()
        list with content to be displayed, defaults to empty list

    checked : list()
        list which stores the checked items from data

    Notes
    -----
    This model only returns strings, so any value entered will be converted to a string
    """

    def __init__(self, data, checked, one_check=False):
        super().__init__(data)
        self.one_check = one_check

        if data is None:
            self._data = list()
        else:
            self._data = data

        if checked is None:
            self._checked = list()
        else:
            self._checked = checked

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            return str(self.getData(index))

        if role == Qt.CheckStateRole:
            if self.getData(index) in self._checked:
                return Qt.Checked
            else:
                return Qt.Unchecked

    def setData(self, index, value, role=None):
        if role == Qt.CheckStateRole:
            if value == Qt.Checked:
                if self.one_check:
                    self._checked.clear()
                self._checked.append(self.getData(index))
            else:
                if self.getData(index) in self._checked:
                    self._checked.remove(self.getData(index))
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index=QModelIndex()):
        return QAbstractItemModel.flags(self, index) | Qt.ItemIsUserCheckable


class CheckDictModel(BaseListModel):
    def __init__(self, data, check_dict):
        super().__init__(data)
        self._check_dict = check_dict
        self.app = QApplication.instance()

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            return str(self.getData(index))

        elif role == Qt.DecorationRole:
            if self.getData(index) in self._check_dict:
                return self.app.style().standardIcon(QStyle.SP_DialogApplyButton)
            else:
                return self.app.style().standardIcon(QStyle.SP_DialogCancelButton)


class BaseDictModel(QAbstractTableModel):
    """Basic Model for Dictonaries

    Parameters
    ----------
    data : dict | None
        Dictionary with keys and values to be displayed, default to empty Dictionary

    Notes
    -----
    Python 3.7 is required to ensure order in dictionary
    """

    def __init__(self, data=None):
        super().__init__()
        if data is None:
            self._data = dict()
        else:
            self._data = data

    def getData(self, index=QModelIndex()):
        try:
            if index.column() == 0:
                return list(self._data.keys())[index.row()]
            elif index.column() == 1:
                return list(self._data.values())[index.row()]
        # Happens, when a duplicate key is entered
        except IndexError:
            self.layoutChanged.emit()
            return ''

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            return str(self.getData(index))

    def headerData(self, idx, orientation, role=None):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if idx == 0:
                    return 'Key'
                elif idx == 1:
                    return 'Value'
            elif orientation == Qt.Vertical:
                return str(idx)

    def rowCount(self, index=QModelIndex()):
        return len(self._data)

    def columnCount(self, index=QModelIndex()):
        return 2


class EditDictModel(BaseDictModel):
    """An editable model for Dictionaries

    Parameters
    ----------
    data : dict | None
        Dictionary with keys and values to be displayed and edited, default to empty Dictionary.

    only_edit : 'keys' | 'values' | None
        Makes only keys or only values editable. Both are editable if None.

    Notes
    -----
    Python 3.7 is required to ensure order in dictionary
    """

    def __init__(self, data=None, only_edit=None):
        super().__init__(data)
        self.only_edit = only_edit

    def setData(self, index, value, role=None):
        if role == Qt.EditRole:
            try:
                value = literal_eval(value)
            except (SyntaxError, ValueError):
                pass
            if index.column() == 0:
                self._data[value] = self._data.pop(list(self._data.keys())[index.row()])
            elif index.column() == 1:
                self._data[list(self._data.keys())[index.row()]] = value
            else:
                return False

            self.dataChanged.emit(index, index, [role])
            return True

        return False

    def flags(self, index=QModelIndex()):
        if not self.only_edit:
            return QAbstractItemModel.flags(self, index) | Qt.ItemIsEditable
        elif index.column() == 0 and self.only_edit == 'keys':
            return QAbstractItemModel.flags(self, index) | Qt.ItemIsEditable
        elif index.column() == 1 and self.only_edit == 'values':
            return QAbstractItemModel.flags(self, index) | Qt.ItemIsEditable
        else:
            return QAbstractItemModel.flags(self, index)

    def insertRows(self, row, count, index=QModelIndex()):
        self.beginInsertRows(index, row, row + count - 1)
        for n in range(count):
            key_name = f'__new{n}__'
            while key_name in self._data.keys():
                n += 1
                key_name = f'__new{n}__'
            self._data[key_name] = ''
        self.endInsertRows()

        return True

    def removeRows(self, row, count, index=QModelIndex()):
        self.beginRemoveRows(index, row, row + count - 1)
        for n in range(count):
            self._data.pop(list(self._data.keys())[row + n])
        self.endRemoveRows()

        return True


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
            self._data = pd.DataFrame([])
        else:
            self._data = data

    def getData(self, index=QModelIndex()):
        return self._data.iloc[index.row(), index.column()]

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            return str(self.getData(index))

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
                value = literal_eval(value)
                # List or Dictionary not allowed here as PandasDataFrame-Item
                if isinstance(value, dict) or isinstance(value, list):
                    value = str(value)
            except (SyntaxError, ValueError):
                pass
            self._data.iloc[index.row(), index.column()] = value
            self.dataChanged.emit(index, index, [role])
            return True

        return False

    def setHeaderData(self, index, orientation, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            if orientation == Qt.Vertical:
                # DataFrame.rename does rename all duplicate indices if existent,
                # that's why the index is reassigned directly
                new_index = list(self._data.index)
                new_index[index] = value
                self._data.index = new_index
                self.headerDataChanged.emit(Qt.Vertical, index, index)
                return True

            elif orientation == Qt.Horizontal:
                # DataFrame.rename does rename all duplicate columns if existent,
                # that's why the columns are reassigned directly
                new_columns = list(self._data.columns)
                new_columns[index] = value
                self._data.columns = new_columns
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
            self._data = pd.concat([self._data, add_data], axis=1)
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


class AddFilesModel(BasePandasModel):
    def __init__(self, data):
        super().__init__(data)

    def data(self, index, role=None):
        column = self._data.columns[index.column()]

        if role == Qt.DisplayRole:
            if column != 'Empty-Room?':
                return str(self.getData(index))
            else:
                return ''

        elif role == Qt.CheckStateRole:
            if column == 'Empty-Room?':
                if self.getData(index):
                    return Qt.Checked
                else:
                    return Qt.Unchecked

    def setData(self, index, value, role=None):
        if role == Qt.CheckStateRole and self._data.columns[index.column()] == 'Empty-Room?':
            if value == Qt.Checked:
                self._data.iloc[index.row(), index.column()] = 1
            else:
                self._data.iloc[index.row(), index.column()] = 0
            self.dataChanged.emit(index, index, [role])
            return True

        return False

    def flags(self, index=QModelIndex()):
        if self._data.columns[index.column()] == 'Empty-Room?':
            return QAbstractItemModel.flags(self, index) | Qt.ItemIsUserCheckable

        return QAbstractItemModel.flags(self, index)

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


class CustomFunctionModel(QAbstractListModel):
    """A Model for the Pandas-DataFrames containing information for new custom functions/their paramers
    Parameters to display only their name and if they are ready
    ----------
    data : DataFrame
    add_pd_funcs or add_pd_params
    """

    def __init__(self, data):
        super().__init__()
        self._data = data
        self.app = QApplication.instance()

    def getData(self, index=QModelIndex()):
        return self._data.index[index.row()]

    def updateData(self, new_data):
        self._data = new_data
        self.layoutChanged.emit()

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            return str(self.getData(index))

        elif role == Qt.DecorationRole:
            if self._data.loc[self.getData(index), 'ready']:
                return self.app.style().standardIcon(QStyle.SP_DialogApplyButton)
            else:
                return self.app.style().standardIcon(QStyle.SP_DialogCancelButton)

    def rowCount(self, index=QModelIndex()):
        return len(self._data.index)


class RunModel(QAbstractListModel):
    """A model for the items/functions of a Pipeline-Run
    """

    def __init__(self, data, mode):
        super().__init__()
        self.app = QApplication.instance()
        self._data = data
        self.mode = mode

    def getKey(self, index=QModelIndex()):
        return list(self._data.keys())[index.row()]

    def getValue(self, index=QModelIndex()):
        if self.mode == 'object':
            return self._data[self.getKey(index)]['status']
        else:
            return self._data[self.getKey(index)]

    def getType(self, index=QModelIndex()):
        return self._data[self.getKey(index)]['type']

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            if self.mode == 'object':
                return f'{self.getType(index)}: {self.getKey(index)}'
            return self.getKey(index)

        # Object/Function-States:
        # 0 = Finished
        # 1 = Pending
        # 2 = Currently Runnning
        # Return Foreground depending on state of object/function
        elif role == Qt.ForegroundRole:
            if self.getValue(index) == 0:
                return QBrush(Qt.darkGray)
            elif self.getValue(index) == 1:
                return QBrush(Qt.darkBlue)
            elif self.getValue(index) == 2:
                return QBrush(Qt.darkGreen)

        # Return Background depending on state of object/function
        elif role == Qt.BackgroundRole:
            if self.getValue(index) == 0:
                return QBrush(Qt.lightGray)
            elif self.getValue(index) == 1:
                return QBrush(Qt.blue)
            elif self.getValue(index) == 2:
                return QBrush(Qt.green)

        # Mark objects/functions if they are already done, mark objects according to their type (color-code)
        elif role == Qt.DecorationRole:
            if self.getValue(index) == 0:
                return self.app.style().standardIcon(QStyle.SP_DialogApplyButton)
            elif self.getValue(index) == 2:
                return self.app.style().standardIcon(QStyle.SP_ArrowRight)

        elif role == Qt.FontRole:
            if self.getValue(index) == 2:
                bold_font = QFont()
                bold_font.setBold(True)
                return bold_font

    def rowCount(self, index=QModelIndex()):
        return len(self._data)
