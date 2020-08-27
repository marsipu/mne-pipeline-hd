import sys
from inspect import getsourcefile
from os.path import abspath
from pathlib import Path

import pandas
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication, QCheckBox, QGridLayout, QInputDialog, QListView, QPushButton, QSpinBox, \
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


class EditPandasTable(QWidget):
    """A Widget to display and edit a pandas DataFrame
    """
    def __init__(self, data=pandas.DataFrame([]), parent=None):
        super().__init__(parent)
        self.data = data

        self.model = EditPandasModel(data)
        self.view = QTableView()
        self.view.setModel(self.model)

        self.layout = QGridLayout()

        self.rows_chkbx = QSpinBox()
        self.rows_chkbx.setMinimum(1)
        self.cols_chkbx = QSpinBox()
        self.cols_chkbx.setMinimum(1)

        self.init_ui()

    def init_ui(self):
        self.layout.addWidget(self.view, 0, 0, 7, 1)

        addr_bt = QPushButton('Add Row')
        addr_bt.clicked.connect(self.add_row)
        self.layout.addWidget(addr_bt, 0, 1)

        self.layout.addWidget(self.rows_chkbx, 0, 2)

        addc_bt = QPushButton('Add Column')
        addc_bt.clicked.connect(self.add_column)
        self.layout.addWidget(addc_bt, 1, 1)

        self.layout.addWidget(self.cols_chkbx, 1, 2)

        rmr_bt = QPushButton('Remove Row')
        rmr_bt.clicked.connect(self.remove_row)
        self.layout.addWidget(rmr_bt, 2, 1, 1, 2)

        rmc_bt = QPushButton('Remove Column')
        rmc_bt.clicked.connect(self.remove_column)
        self.layout.addWidget(rmc_bt, 3, 1, 1, 2)

        edit_bt = QPushButton('Edit')
        edit_bt.clicked.connect(self.edit_item)
        self.layout.addWidget(edit_bt, 4, 1, 1, 2)

        editrh_bt = QPushButton('Edit Row-Header')
        editrh_bt.clicked.connect(self.edit_row_header)
        self.layout.addWidget(editrh_bt, 5, 1, 1, 2)

        editch_bt = QPushButton('Edit Column-Header')
        editch_bt.clicked.connect(self.edit_col_header)
        self.layout.addWidget(editch_bt, 6, 1, 1, 2)

        self.setLayout(self.layout)

    def content_changed(self):
        """Informs ModelView about change in data
        """
        self.model.layoutChanged.emit()

    def update_data(self):
        """You can overwrite this function in a subclass e.g. to update an objects attribute

        Returns
        -------
        data : pandas.DataFrame
            The DataFrame of this widget
        """
        self.data = self.model._data

        return self.data

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
