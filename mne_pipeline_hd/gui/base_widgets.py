import sys
from inspect import getsourcefile
from os.path import abspath
from pathlib import Path

import pandas
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication, QCheckBox, QGridLayout, QHBoxLayout, QInputDialog, QListView, QPushButton, \
    QSpinBox, \
    QTabWidget, \
    QTableView, \
    QVBoxLayout, \
    QWidget

package_parent = str(Path(abspath(getsourcefile(lambda: 0))).parent.parent.parent)
sys.path.insert(0, package_parent)

from mne_pipeline_hd.gui.models import (BaseListModel, BasePandasModel, CheckListModel, EditListModel, EditPandasModel)


class BaseList(QWidget):
    """A basic List-Widget to display the content of a list.

    Parameters
    ----------
    data : List of str | None
        Input a list with contents to display
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent

    Notes
    -----
    If you change the list outside of this class, call content_changed to update this widget
    """

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.data = data or list()

        self.model = BaseListModel(self.data)
        self.view = QListView()
        self.view.setModel(self.model)

        self.layout = QVBoxLayout()

        self.init_ui()

    def init_ui(self):
        self.layout.addWidget(self.view)
        self.setLayout(self.layout)

    def content_changed(self):
        """Informs ModelView about change in data
        """
        self.model.layoutChanged.emit()

    def replace_data(self, new_data):
        """Replaces model._data with new_data
        """
        self.model._data = new_data
        self.content_changed()

class EditList(QWidget):
    """An editable List-Widget to display and manipulate the content of a list.

    Parameters
    ----------
    data : List of str | None
        Input a list with contents to display
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent

    Notes
    -----
    If you change the list outside of this class, call content_changed to update this widget
    """

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.data = data or list()

        self.model = EditListModel(self.data)
        self.view = QListView()
        self.view.setModel(self.model)

        self.layout = QGridLayout()

        self.init_ui()

    def init_ui(self):
        self.layout.addWidget(self.view, 0, 0, 3, 1)

        addrow_bt = QPushButton('Add Row')
        addrow_bt.clicked.connect(self.add_row)
        self.layout.addWidget(addrow_bt, 0, 1)

        rmrow_bt = QPushButton('Remove Row')
        rmrow_bt.clicked.connect(self.remove_row)
        self.layout.addWidget(rmrow_bt, 2, 1)

        edit_bt = QPushButton('Edit')
        edit_bt.clicked.connect(self.edit_item)
        self.layout.addWidget(edit_bt, 3, 1)

        self.setLayout(self.layout)

    def content_changed(self):
        """Informs ModelView about change in data
        """
        self.model.layoutChanged.emit()

    def replace_data(self, new_data):
        """Replaces model._data with new_data
        """
        self.model._data = new_data
        self.content_changed()

    def add_row(self):
        row = self.view.selectionModel().currentIndex().row()
        self.model.insertRow(row)

    def remove_row(self):
        row_idxs = self.view.selectionModel().selectedRows()
        for row_idx in row_idxs:
            self.model.removeRow(row_idx.row())

    def edit_item(self):
        self.view.edit(self.view.selectionModel().currentIndex())


class CheckList(QWidget):
    """A Widget for a Check-List.

    Parameters
    ----------
    data : List of str | None
        Input a list with contents to display
    checked : List of str | None
        Input a list, which will contain the checked items from data (and which intial items will be checked)
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent

    Notes
    -----
    If you change the list outside of this class, call content_changed to update this widget
    """

    def __init__(self, data=None, checked=None, parent=None):
        super().__init__(parent)
        self.data = data or list()
        self.checked = checked or list()

        self.model = CheckListModel(self.data, self.checked)
        self.view = QListView()
        self.view.setModel(self.model)

        self.layout = QVBoxLayout()

        self.init_ui()

    def init_ui(self):
        self.layout.addWidget(self.view)
        self.setLayout(self.layout)

    def content_changed(self):
        """Informs ModelView about change in data
        """
        self.model.layoutChanged.emit()

    def replace_data(self, new_data, new_checked):
        """Replaces model._data with new_data
        """
        self.model._data = new_data
        self.model._checked = new_checked
        self.content_changed()


class BasePandasTable(QWidget):
    """A Widget to display a pandas DataFrame

    Parameters
    ----------
    data : pandas.DataFrame | None
        Input a pandas DataFrame with contents to display
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent

    Notes
    -----
    If you change the DataFrame outside of this class, call content_changed to update this widget
    """

    def __init__(self, data=pandas.DataFrame([]), parent=None):
        super().__init__(parent)
        self.data = data

        self.model = BasePandasModel(self.data)
        self.view = QTableView()
        self.view.setModel(self.model)

        self.layout = QVBoxLayout()

        self.init_ui()

    def init_ui(self):
        self.layout.addWidget(self.view)
        self.setLayout(self.layout)

    def content_changed(self):
        """Informs ModelView about change in data
        """
        self.model.layoutChanged.emit()

    def replace_data(self, new_data):
        """Replaces model._data with new_data
        """
        self.model._data = new_data
        self.content_changed()

class EditPandasTable(QWidget):
    """A Widget to display and edit a pandas DataFrame
    """
    def __init__(self, data=pandas.DataFrame([]), ui_buttons=True, parent=None):
        super().__init__(parent)
        self.data = data
        self.ui_buttons = ui_buttons

        self.model = EditPandasModel(data)
        self.view = QTableView()
        self.view.setModel(self.model)

        self.layout = QHBoxLayout()

        self.rows_chkbx = QSpinBox()
        self.rows_chkbx.setMinimum(1)
        self.cols_chkbx = QSpinBox()
        self.cols_chkbx.setMinimum(1)

        self.init_ui()

    def init_ui(self):
        self.layout.addWidget(self.view)

        if self.ui_buttons:
            bt_layout = QVBoxLayout()

            addr_layout = QHBoxLayout()
            addr_bt = QPushButton('Add Row')
            addr_bt.clicked.connect(self.add_row)
            addr_layout.addWidget(addr_bt)
            addr_layout.addWidget(self.rows_chkbx)
            bt_layout.addLayout(addr_layout)

            addc_layout = QHBoxLayout()
            addc_bt = QPushButton('Add Column')
            addc_bt.clicked.connect(self.add_column)
            addc_layout.addWidget(addc_bt)
            addc_layout.addWidget(self.cols_chkbx)
            bt_layout.addLayout(addc_layout)

            rmr_bt = QPushButton('Remove Row')
            rmr_bt.clicked.connect(self.remove_row)
            bt_layout.addWidget(rmr_bt)

            rmc_bt = QPushButton('Remove Column')
            rmc_bt.clicked.connect(self.remove_column)
            bt_layout.addWidget(rmc_bt)

            edit_bt = QPushButton('Edit')
            edit_bt.clicked.connect(self.edit_item)
            bt_layout.addWidget(edit_bt)

            editrh_bt = QPushButton('Edit Row-Header')
            editrh_bt.clicked.connect(self.edit_row_header)
            bt_layout.addWidget(editrh_bt)

            editch_bt = QPushButton('Edit Column-Header')
            editch_bt.clicked.connect(self.edit_col_header)
            bt_layout.addWidget(editch_bt)

            self.layout.addLayout(bt_layout)

        self.setLayout(self.layout)

    def content_changed(self):
        """Informs ModelView about change in data
        """
        self.model.layoutChanged.emit()

    def update_data(self):
        """Has to be called, when model._data is rereferenced to keep self.data updated

        Returns
        -------
        data : pandas.DataFrame
            The DataFrame of this widget

        Notes
        -----
        You can overwrite this function in a subclass e.g. to update an objects attribute
        """
        self.data = self.model._data

        return self.data

    def replace_data(self, new_data):
        """Replaces model._data with new_data
        """
        self.model._data = new_data
        self.content_changed()

    def add_row(self):
        row = self.view.selectionModel().currentIndex().row()
        if row == -1:
            row = len(self.data.index)
        self.model.insertRows(row, self.rows_chkbx.value())
        self.update_data()

    def add_column(self):
        column = self.view.selectionModel().currentIndex().column()
        if column == -1:
            column = len(self.data.columns)
        self.model.insertColumns(column, self.cols_chkbx.value())
        self.update_data()

    def remove_row(self):
        rows = sorted(set([ix.row() for ix in self.view.selectionModel().selectedIndexes()]), reverse=True)
        for row in rows:
            self.model.removeRow(row)
        self.update_data()

    def remove_column(self):
        columns = sorted(set([ix.column() for ix in self.view.selectionModel().selectedIndexes()]), reverse=True)
        for column in columns:
            self.model.removeColumn(column)
        self.update_data()

    def edit_item(self):
        self.view.edit(self.view.selectionModel().currentIndex())

    def edit_row_header(self):
        row = self.view.selectionModel().currentIndex().row()
        old_value = self.data.index[row]
        text, ok = QInputDialog.getText(self, 'Change Row-Header', f'Change {old_value} in row {row} to:')
        if text and ok:
            self.model.setHeaderData(row, Qt.Vertical, text)

    def edit_col_header(self):
        column = self.view.selectionModel().currentIndex().column()
        old_value = self.data.columns[column]
        text, ok = QInputDialog.getText(self, 'Change Column-Header', f'Change {old_value} in column {column} to:')
        if text and ok:
            self.model.setHeaderData(column, Qt.Horizontal, text)


class AllBaseWidgets(QWidget):
    def __init__(self):
        super().__init__()

        self.exlist = ['Athena', 'Hephaistos', 'Zeus', 'Ares', 'Aphrodite', 'Poseidon']
        self.exchecked = ['Athena']
        self.expd = pandas.DataFrame([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]], columns=['A', 'B', 'C', 'D'])
        self.extree = {'A': {'Aa': 1,
                             'Ab': {'Ab1': 'Hermes',
                                    'Ab2': 'Hades'},
                             'Ac': [1, 2, 3, 4]},
                       'B': ['Appolo', 42, 128],
                       'C': (1, 2, 3)}

        # self.exlist = None
        # self.exchecked = None
        # self.expd = None
        # self.extree = None

        self.widget_dict = {'BaseList': [self.exlist],
                            'EditList': [self.exlist],
                            'CheckList': [self.exlist, self.exchecked],
                            'BasePandasTable': [self.expd],
                            'EditPandasTable': [self.expd]}

        self.layout = QVBoxLayout()
        self.tab_widget = QTabWidget()

        self.init_ui()

        self.setGeometry(0, 0, 800, 400)

    def init_ui(self):
        for widget in self.widget_dict:
            self.tab_widget.addTab(globals()[widget](*self.widget_dict[widget]), widget)

        self.layout.addWidget(self.tab_widget)
        self.setLayout(self.layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    testw = AllBaseWidgets()
    testw.show()

    # Command-Line interrupt with Ctrl+C possible, easier debugging
    timer = QTimer()
    timer.timeout.connect(lambda: testw)
    timer.start(500)

    sys.exit(app.exec())
