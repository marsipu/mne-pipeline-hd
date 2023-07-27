# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""

from ast import literal_eval
from datetime import datetime

import pandas as pd
from PyQt5.QtCore import (
    QAbstractItemModel,
    QAbstractListModel,
    QAbstractTableModel,
    QModelIndex,
    Qt,
)
from PyQt5.QtGui import QBrush, QFont

from mne_pipeline_hd.gui.gui_utils import get_std_icon


class BaseListModel(QAbstractListModel):
    """A basic List-Model

    Parameters
    ----------
    data : list()
        input existing list here, otherwise defaults to empty list
    show_index : bool
        Set True if you want to display the list-index in front of each value
    drag_drop: bool
        Set True to enable Drag&Drop.
    """

    def __init__(self, data=None, show_index=False, drag_drop=False, **kwargs):
        super().__init__(**kwargs)
        self.show_index = show_index
        self.drag_drop = drag_drop
        if data is None:
            self._data = list()
        else:
            self._data = data

    def getData(self, index):
        return self._data[index.row()]

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            if self.show_index:
                return f"{index.row()}: {self.getData(index)}"
            else:
                return str(self.getData(index))
        elif role == Qt.EditRole:
            return str(self.getData(index))

    def rowCount(self, index):
        return len(self._data)

    def insertRows(self, row, count, index):
        self.beginInsertRows(index, row, row + count - 1)
        n = 0
        for pos in range(row, row + count):
            item_name = f"__new{n}__"
            while item_name in self._data:
                n += 1
                item_name = f"__new{n}__"
            self._data.insert(pos, item_name)
        self.endInsertRows()
        return True

    def removeRows(self, row, count, index):
        self.beginRemoveRows(index, row, row + count - 1)
        for item in [self._data[i] for i in range(row, row + count)]:
            self._data.remove(item)
        self.endRemoveRows()
        return True

    def flags(self, index):
        default_flags = QAbstractListModel.flags(self, index)
        if self.drag_drop:
            if index.isValid():
                return default_flags | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
            else:
                return default_flags | Qt.ItemIsDropEnabled
        else:
            return default_flags

    def supportedDragActions(self):
        if self.drag_drop:
            return Qt.CopyAction | Qt.MoveAction


class EditListModel(BaseListModel):
    """An editable List-Model

    Parameters
    ----------
    data : list()
        input existing list here, otherwise defaults to empty list
    show_index: bool
        Set True if you want to display the list-index in front of each value
    drag_drop: bool
        Set True to enable Drag&Drop.
    """

    def __init__(self, data, show_index=False, drag_drop=False, **kwargs):
        super().__init__(data, show_index, drag_drop, **kwargs)

    def flags(self, index):
        default_flags = BaseListModel.flags(self, index)
        if index.isValid():
            return default_flags | Qt.ItemIsEditable
        else:
            return default_flags

    def setData(self, index, value, role=None):
        if role == Qt.EditRole:
            try:
                self._data[index.row()] = literal_eval(value)
            except (ValueError, SyntaxError):
                self._data[index.row()] = value
            self.dataChanged.emit(index, index)
            return True
        return False


class CheckListModel(BaseListModel):
    """
    A Model for a Check-List

    Parameters
    ----------
    data : list()
        list with content to be displayed, defaults to empty list
    checked : list()
        list which stores the checked items from data
    show_index: bool
        Set True if you want to display the list-index in front of each value
    drag_drop: bool
        Set True to enable Drag&Drop.

    """

    def __init__(
        self,
        data,
        checked,
        one_check=False,
        show_index=False,
        drag_drop=False,
        **kwargs,
    ):
        super().__init__(data, show_index, drag_drop, **kwargs)
        self.one_check = one_check

        if data is None:
            self._data = list()
        else:
            self._data = data

        if checked is None:
            self._checked = list()
        else:
            self._checked = checked

    def getChecked(self, index):
        return self.checked[index.row()]

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            if self.show_index:
                return f"{index.row()}: {self.getData(index)}"
            else:
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

    def flags(self, index):
        return QAbstractItemModel.flags(self, index) | Qt.ItemIsUserCheckable


class CheckDictModel(BaseListModel):
    """
    A Model for a list, which marks items which are present in a dictionary

    Parameters
    ----------
    data : list()
        list with content to be displayed, defaults to empty list
    check_dict : dict()
        dictionary which may contain items from data as keys
    show_index: bool
        Set True if you want to display the list-index in front of each value
    drag_drop: bool
        Set True to enable Drag&Drop.
    yes_bt: str
        Supply the name for a qt-standard-icon to mark the items
        existing in check_dict
    no_bt: str
        Supply the name for a qt-standard-icon to mark the items
        not existing in check_dict

    Notes
    -----
    Names for QT standard-icons:
    https://doc.qt.io/qt-5/qstyle.html#StandardPixmap-enum
    """

    def __init__(
        self,
        data,
        check_dict,
        show_index=False,
        drag_drop=False,
        yes_bt=None,
        no_bt=None,
        **kwargs,
    ):
        super().__init__(data, show_index, drag_drop, **kwargs)
        self._check_dict = check_dict

        self.yes_bt = yes_bt or "SP_DialogApplyButton"
        self.no_bt = no_bt or "SP_DialogCancelButton"

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            if self.show_index:
                return f"{index.row()}: {self.getData(index)}"
            else:
                return str(self.getData(index))
        elif role == Qt.EditRole:
            return str(self.getData(index))

        elif role == Qt.DecorationRole:
            if self.getData(index) in self._check_dict:
                return get_std_icon(self.yes_bt)
            else:
                return get_std_icon(self.no_bt)


class CheckDictEditModel(CheckDictModel, EditListModel):
    """An editable List-Model

    Parameters
    ----------
    data : list()
        list with content to be displayed, defaults to empty list
    check_dict : dict()
        dictionary which may contain items from data as keys
    show_index: bool
        Set True if you want to display the list-index in front of each value
    drag_drop: bool
        Set True to enable Drag&Drop.
    yes_bt: str
        Supply the name for a qt-standard-icon to mark the items
         existing in check_dict
    no_bt: str
        Supply the name for a qt-standard-icon to mark the items
        not existing in check_dict

    Notes
    -----
    Names for QT standard-icons:
    https://doc.qt.io/qt-5/qstyle.html#StandardPixmap-enum
    """

    def __init__(
        self,
        data,
        check_dict,
        show_index=False,
        drag_drop=False,
        yes_bt=None,
        no_bt=None,
    ):
        super().__init__(data, check_dict, show_index, drag_drop, yes_bt, no_bt)
        # EditListModel doesn't have to be initialized
        # because in __init__ of EditListModel
        # only BaseListModel is initialized which is already done
        # in __init__ of CheckDictModel


class BaseDictModel(QAbstractTableModel):
    """Basic Model for Dictonaries

    Parameters
    ----------
    data : dict | OrderedDict | None
        Dictionary with keys and values to be displayed,
         default to empty Dictionary

    Notes
    -----
    Python 3.7 is required to ensure order in dictionary
     when inserting a normal dict (or use OrderedDict)
    """

    def __init__(self, data=None, **kwargs):
        super().__init__(**kwargs)
        if data is None:
            self._data = dict()
        else:
            self._data = data

    def getData(self, index):
        try:
            if index.column() == 0:
                return list(self._data.keys())[index.row()]
            elif index.column() == 1:
                return list(self._data.values())[index.row()]
        # Happens, when a duplicate key is entered
        except IndexError:
            self.layoutChanged.emit()
            return ""

    def data(self, index, role=None):
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return str(self.getData(index))

    def headerData(self, idx, orientation, role=None):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if idx == 0:
                    return "Key"
                elif idx == 1:
                    return "Value"
            elif orientation == Qt.Vertical:
                return str(idx)

    def rowCount(self, index):
        return len(self._data)

    def columnCount(self, index):
        return 2


class EditDictModel(BaseDictModel):
    """An editable model for Dictionaries

    Parameters
    ----------
    data : dict | OrderedDict | None
        Dictionary with keys and values to be displayed,
         default to empty Dictionary

    only_edit : 'keys' | 'values' | None
        Makes only keys or only values editable. Both are editable if None.

    Notes
    -----
    Python 3.7 is required to ensure order in dictionary
     when inserting a normal dict (or use OrderedDict)
    """

    def __init__(self, data=None, only_edit=None, **kwargs):
        super().__init__(data, **kwargs)
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

    def flags(self, index):
        if not self.only_edit:
            return QAbstractItemModel.flags(self, index) | Qt.ItemIsEditable
        elif index.column() == 0 and self.only_edit == "keys":
            return QAbstractItemModel.flags(self, index) | Qt.ItemIsEditable
        elif index.column() == 1 and self.only_edit == "values":
            return QAbstractItemModel.flags(self, index) | Qt.ItemIsEditable
        else:
            return QAbstractItemModel.flags(self, index)

    def insertRows(self, row, count, index):
        self.beginInsertRows(index, row, row + count - 1)
        for n in range(count):
            key_name = f"__new{n}__"
            while key_name in self._data.keys():
                n += 1
                key_name = f"__new{n}__"
            self._data[key_name] = ""
        self.endInsertRows()

        return True

    def removeRows(self, row, count, index):
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
        pandas DataFrame with contents to be displayed,
        defaults to empty DataFrame
    """

    def __init__(self, data=None, **kwargs):
        super().__init__(**kwargs)
        if data is None:
            self._data = pd.DataFrame([])
        else:
            self._data = data

    def getData(self, index):
        return self._data.iloc[index.row(), index.column()]

    def data(self, index, role=None):
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return str(self.getData(index))

    def headerData(self, idx, orientation, role=None):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[idx])
            elif orientation == Qt.Vertical:
                return str(self._data.index[idx])

    def rowCount(self, index):
        return len(self._data.index)

    def columnCount(self, index):
        return len(self._data.columns)


class EditPandasModel(BasePandasModel):
    """Editable TableModel for Pandas DataFrames
    Parameters
    ----------
    data : pandas.DataFrame | None
        pandas DataFrame with contents to be displayed,
         defaults to empty DataFrame

    Notes
    -----
    The reference of the original input-DataFrame is lost
     when edited by this Model,
    you need to retrieve it directly from the model after editing
    """

    def __init__(self, data=None, **kwargs):
        super().__init__(data, **kwargs)

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
                # DataFrame.rename does rename all duplicate indices
                # if existent, that's why the index is reassigned directly
                new_index = list(self._data.index)
                new_index[index] = value
                self._data.index = new_index
                self.headerDataChanged.emit(Qt.Vertical, index, index)
                return True

            elif orientation == Qt.Horizontal:
                # DataFrame.rename does rename all duplicate columns
                # if existent, that's why the columns are reassigned directly
                new_columns = list(self._data.columns)
                new_columns[index] = value
                self._data.columns = new_columns
                self.headerDataChanged.emit(Qt.Horizontal, index, index)
                return True

        return False

    def flags(self, index):
        return QAbstractItemModel.flags(self, index) | Qt.ItemIsEditable

    def insertRows(self, row, count, index):
        self.beginInsertRows(index, row, row + count - 1)
        add_data = pd.DataFrame(
            columns=self._data.columns, index=[r for r in range(count)]
        )
        if row == 0:
            self._data = pd.concat([add_data, self._data])
        elif row == len(self._data.index):
            self._data = self._data.append(add_data)
        else:
            self._data = pd.concat(
                [self._data.iloc[:row], add_data, self._data.iloc[row:]]
            )
        self.endInsertRows()

        return True

    def insertColumns(self, column, count, index):
        self.beginInsertColumns(index, column, column + count - 1)
        add_data = pd.DataFrame(
            index=self._data.index, columns=[c for c in range(count)]
        )
        if column == 0:
            self._data = pd.concat([add_data, self._data], axis=1)
        elif column == len(self._data.columns):
            self._data = pd.concat([self._data, add_data], axis=1)
        else:
            self._data = pd.concat(
                [self._data.iloc[:, :column], add_data, self._data.iloc[:, column:]],
                axis=1,
            )
        self.endInsertColumns()

        return True

    def removeRows(self, row, count, index):
        self.beginRemoveRows(index, row, row + count - 1)
        # Can't use DataFrame.drop() here,
        # because there could be rows with similar index-labels
        if row == 0:
            self._data = self._data.iloc[row + count :]
        elif row + count >= len(self._data.index):
            self._data = self._data.iloc[:row]
        else:
            self._data = pd.concat(
                [self._data.iloc[:row], self._data.iloc[row + count :]]
            )
        self.endRemoveRows()

        return True

    def removeColumns(self, column, count, index):
        self.beginRemoveColumns(index, column, column + count - 1)
        # Can't use DataFrame.drop() here,
        # because there could be columns with similar column-labels
        if column == 0:
            self._data = self._data.iloc[:, column + count :]
        elif column + count >= len(self._data.columns):
            self._data = self._data.iloc[:, :column]
        else:
            self._data = pd.concat(
                [self._data.iloc[:, :column], self._data.iloc[:, column + count :]],
                axis=1,
            )
        self.endRemoveColumns()

        return True


class TreeItem:
    """TreeItem as in
    https://doc.qt.io/qt-5/qtwidgets-itemviews-simpletreemodel-example.html"""

    def __init__(self, data, parent=None):
        self._data = data
        self._parent = parent
        self._children = list()

    def child(self, number):
        if 0 <= number < len(self._children):
            return self._children[number]

    def childCount(self):
        return len(self._children)

    def row(self):
        if self._parent:
            return self._parent._children.index(self)
        return 0

    def columnCount(self):
        return len(self._data)

    def data(self, column):
        if 0 <= column < len(self._data):
            return self._data[column]

    def setData(self, column, value):
        if 0 <= column < len(self._data):
            self._data[column] = value
            return True
        return False

    def insertChild(self, position):
        if 0 <= position < len(self._children):
            self._children.insert(
                position, TreeItem([f"__new__{len(self._children)}"], self)
            )
            return True
        return False

    def removeChild(self, position):
        if 0 <= position < len(self._children):
            self._children.remove(self._children[position])
            return True
        return False

    def insertColumn(self, position):
        if 0 <= position < len(self._data):
            self._data.insert(position, f"__new__{len(self._data)}")
            for child in self._children:
                child.insertColumns(position)
            return True
        return False

    def removeColumn(self, position):
        if 0 <= position < len(self._data):
            self._data.remove(self._data[position])
            for child in self._children:
                child.removeColumns(position)
            return True
        return False


class TreeModel(QAbstractItemModel):
    """Tree-Model as in
    https://doc.qt.io/qt-5/qtwidgets-itemviews-simpletreemodel-example.html"""

    def __init__(self, data, n_columns=1, headers=None, parent=None):
        super().__init__(parent)
        self._data = data
        self._n_columns = n_columns
        if headers is None:
            headers = ["" for i in range(n_columns)]
        elif len(headers) < n_columns:
            headers += ["" for i in range(n_columns - headers)]
        elif len(headers) > n_columns:
            headers = headers[:n_columns]
        self._headers = headers
        self._parent = parent

        self.root_item = self.dict_to_items(self._data)

    def dict_to_items(self, datadict, parent=None):
        if parent is None:
            parent = TreeItem(self._headers)

        for key, value in datadict.items():
            data = [key] + ["" for i in range(self._n_columns - 1)]
            tree_item = TreeItem(data, parent)
            if isinstance(value, dict):
                child_item = self.dict_to_items(value, tree_item)
                tree_item._children.append(child_item)
            parent._children.append(tree_item)

        return parent

    # noinspection PyMethodMayBeStatic
    def getData(self, index):
        if index.isValid():
            item = index.internalPointer()
            return item.data(index.column())

    def data(self, index: QModelIndex, role: int = ...) -> object:
        if role == Qt.DisplayRole:
            return self.getData(index)

    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        if self.hasIndex(row, column, parent):
            if parent.isValid():
                parentItem = parent.internalPointer()
            else:
                parentItem = self.root_item

            childItem = parentItem.child(row)
            if childItem is not None:
                return self.createIndex(row, column, childItem)
        return QModelIndex()

    def parent(self, child: QModelIndex) -> QModelIndex:
        if child.isValid():
            childItem = child.internalPointer()
            parentItem = childItem._parent

            if parentItem != self.root_item:
                return self.createIndex(parentItem.row(), 0, parentItem)
        return QModelIndex()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        if parent.column() > 0:
            return 0

        if parent.isValid():
            parentItem = parent.internalPointer()
        else:
            parentItem = self.root_item

        return parentItem.childCount()

    def columnCount(self, parent: QModelIndex = ...) -> int:
        if parent.isValid():
            return parent.internalPointer().columnCount()
        return self.root_item.columnCount()

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if index.isValid():
            return QAbstractItemModel.flags(self, index)
        return Qt.NoItemFlags

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = ...
    ) -> object:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            self.root_item.data(section)


class AddFilesModel(BasePandasModel):
    def __init__(self, data, **kwargs):
        super().__init__(data, **kwargs)

    def data(self, index, role=None):
        column = self._data.columns[index.column()]

        if role == Qt.DisplayRole:
            if column != "Empty-Room?":
                return str(self.getData(index))
            else:
                return ""

        elif role == Qt.CheckStateRole:
            if column == "Empty-Room?":
                if self.getData(index):
                    return Qt.Checked
                else:
                    return Qt.Unchecked

    def setData(self, index, value, role=None):
        if (
            role == Qt.CheckStateRole
            and self._data.columns[index.column()] == "Empty-Room?"
        ):
            if value == Qt.Checked:
                self._data.iloc[index.row(), index.column()] = 1
            else:
                self._data.iloc[index.row(), index.column()] = 0
            self.dataChanged.emit(index, index, [role])
            return True

        return False

    def flags(self, index):
        if self._data.columns[index.column()] == "Empty-Room?":
            return QAbstractItemModel.flags(self, index) | Qt.ItemIsUserCheckable

        return QAbstractItemModel.flags(self, index)

    def removeRows(self, row, count, index):
        self.beginRemoveRows(index, row, row + count - 1)
        # Can't use DataFrame.drop() here,
        # because there could be rows with similar index-labels
        if row == 0:
            self._data = self._data.iloc[row + count :]
        elif row + count >= len(self._data.index):
            self._data = self._data.iloc[:row]
        else:
            self._data = pd.concat(
                [self._data.iloc[:row], self._data.iloc[row + count :]]
            )
        self.endRemoveRows()

        return True


class FileManagementModel(BasePandasModel):
    """A model for the Pandas-DataFrames containing information
    about the existing files"""

    def __init__(self, data, **kwargs):
        super().__init__(data, **kwargs)

    def data(self, index, role=None):
        value = self.getData(index)
        if role == Qt.DisplayRole:
            if pd.isna(value) or value in [
                "existst",
                "possible_conflict",
                "critical_conflict",
            ]:
                pass
            elif isinstance(value, datetime):
                return value.strftime("%d.%m.%y %H:%M")
            elif isinstance(value, float):
                if value == 0:
                    pass
                elif value / 1024 < 1000:
                    return f"{int(value / 1024)} KB"
                else:
                    return f"{int(value / (1024 ** 2))} MB"

        if role == Qt.DecorationRole:
            if pd.isna(value) or value == 0:
                return get_std_icon("SP_DialogCancelButton")
            elif value == "exists":
                return get_std_icon("SP_DialogApplyButton")
            elif value == "possible_conflict":
                return get_std_icon("SP_MessageBoxQuestion")
            elif value == "critical_conflict":
                return get_std_icon("SP_MessageBoxWarning")

        elif role == Qt.BackgroundRole:
            if pd.isna(value) or value == 0:
                return QBrush(Qt.darkRed)
            elif value == "exists":
                return QBrush(Qt.green)
            elif value == "possible_conflict":
                return QBrush(Qt.lightGray)
            elif value == "critical_conflict":
                return QBrush(Qt.darkYellow)


class CustomFunctionModel(QAbstractListModel):
    """A Model for the Pandas-DataFrames containing information about
     new custom functions/their paramers to display only their name
     and if they are ready.

    Parameters
    ----------
    data : DataFrame
    add_pd_funcs or add_pd_params
    """

    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self._data = data

    def getData(self, index):
        return self._data.index[index.row()]

    def updateData(self, new_data):
        self._data = new_data
        self.layoutChanged.emit()

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            return str(self.getData(index))

        elif role == Qt.DecorationRole:
            if self._data.loc[self.getData(index), "ready"]:
                return get_std_icon("SP_DialogApplyButton")
            else:
                return get_std_icon("SP_DialogCancelButton")

    def rowCount(self, index):
        return len(self._data.index)


class RunModel(QAbstractListModel):
    """A model for the items/functions of a Pipeline-Run"""

    def __init__(self, data, mode):
        super().__init__()
        self._data = data
        self.mode = mode

    def getKey(self, index):
        return list(self._data.keys())[index.row()]

    def getValue(self, index):
        if self.mode == "object":
            return self._data[self.getKey(index)]["status"]
        else:
            return self._data[self.getKey(index)]

    def getType(self, index):
        return self._data[self.getKey(index)]["type"]

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            if self.mode == "object":
                return f"{self.getType(index)}: {self.getKey(index)}"
            return self.getKey(index)

        # Object/Function-States:
        # 0 = Finished
        # 1 = Pending
        # 2 = Currently Runnning
        # Return Foreground depending on state of object/function
        elif role == Qt.ForegroundRole:
            if self.getValue(index) == 0:
                return QBrush(Qt.darkGray)
            elif self.getValue(index) == 2:
                return QBrush(Qt.green)

        # Return Background depending on state of object/function
        elif role == Qt.BackgroundRole:
            if self.getValue(index) == 2:
                return QBrush(Qt.darkGreen)

        # Mark objects/functions if they are already done,
        # mark objects according to their type (color-code)
        elif role == Qt.DecorationRole:
            if self.getValue(index) == 0:
                return get_std_icon("SP_DialogApplyButton")
            elif self.getValue(index) == 2:
                return get_std_icon("SP_ArrowRight")

        elif role == Qt.FontRole:
            if self.getValue(index) == 2:
                bold_font = QFont()
                bold_font.setBold(True)
                return bold_font

    def rowCount(self, index):
        return len(self._data)
