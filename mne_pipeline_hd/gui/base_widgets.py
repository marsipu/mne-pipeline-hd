import sys
from inspect import getsourcefile
from os.path import abspath
from pathlib import Path

import pandas
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QInputDialog, QListView, QPushButton, QSizePolicy, QSpinBox,
                             QTabWidget, QTableView, QVBoxLayout, QWidget)

package_parent = str(Path(abspath(getsourcefile(lambda: 0))).parent.parent.parent)
sys.path.insert(0, package_parent)

from mne_pipeline_hd.gui.models import (BaseDictModel, BaseListModel, BasePandasModel, CheckListModel, EditDictModel,
                                        EditListModel,
                                        EditPandasModel)


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

        self.model = BaseListModel(data)
        self.view = QListView()
        self.view.setModel(self.model)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

    def content_changed(self):
        """Informs ModelView about external change made in data
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
    ui_buttons : bool
        If to display Buttons or not
    ui_button_pos: str
        The side on which to show the buttons, 'right', 'left', 'top' or 'bottom'
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent

    Notes
    -----
    If you change the list outside of this class, call content_changed to update this widget
    """

    def __init__(self, data=None, ui_buttons=True, ui_button_pos='right', parent=None):
        super().__init__(parent)
        self.ui_buttons = ui_buttons
        self.ui_button_pos = ui_button_pos

        self.model = EditListModel(data)
        self.view = QListView()
        self.view.setModel(self.model)

        self.init_ui()

    def init_ui(self):
        if self.ui_button_pos in ['top', 'bottom']:
            layout = QVBoxLayout()
            bt_layout = QHBoxLayout()
        else:
            layout = QHBoxLayout()
            bt_layout = QVBoxLayout()

        if self.ui_buttons:
            addrow_bt = QPushButton('Add')
            addrow_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            addrow_bt.clicked.connect(self.add_row)
            bt_layout.addWidget(addrow_bt)

            rmrow_bt = QPushButton('Remove')
            rmrow_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            rmrow_bt.clicked.connect(self.remove_row)
            bt_layout.addWidget(rmrow_bt)

            edit_bt = QPushButton('Edit')
            edit_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            edit_bt.clicked.connect(self.edit_item)
            bt_layout.addWidget(edit_bt)

            layout.addLayout(bt_layout)

        if self.ui_button_pos in ['top', 'left']:
            layout.addWidget(self.view)
        else:
            layout.insertWidget(0, self.view)

        self.setLayout(layout)

    def content_changed(self):
        """Informs ModelView about external change made in data
        """
        self.model.layoutChanged.emit()

    def replace_data(self, new_data):
        """Replaces model._data with new_data
        """
        self.model._data = new_data
        self.content_changed()

    def add_row(self):
        row = self.view.selectionModel().currentIndex().row()
        if row == -1:
            row = len(self.model._data)
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
    ui_buttons : bool
        If to display Buttons or not
    one_check : bool
        If only one Item in the CheckList can be checked at the same time
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent

    Notes
    -----
    If you change the list outside of this class, call content_changed to update this widget
    """

    def __init__(self, data=None, checked=None, ui_buttons=True, one_check=False, parent=None):
        super().__init__(parent)
        self.ui_buttons = ui_buttons

        self.model = CheckListModel(data, checked, one_check=one_check)
        self.view = QListView()
        self.view.setModel(self.model)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(self.view)

        if self.ui_buttons:
            bt_layout = QHBoxLayout()

            all_bt = QPushButton('All')
            all_bt.clicked.connect(self.select_all)
            bt_layout.addWidget(all_bt)

            clear_bt = QPushButton('Clear')
            clear_bt.clicked.connect(self.clear_all)
            bt_layout.addWidget(clear_bt)

            layout.addLayout(bt_layout)

        self.setLayout(layout)

    def content_changed(self):
        """Informs ModelView about external change made in data
        """
        self.model.layoutChanged.emit()

    def replace_data(self, new_data, new_checked):
        """Replaces model._data with new_data
        """
        self.model._data = new_data
        self.model._checked = new_checked
        self.content_changed()

    def select_all(self):
        """Select all Items while leaving reference to model._checked intact"""
        for item in [i for i in self.model._data if i not in self.model._checked]:
            self.model._checked.append(item)
        # Inform Model about changes
        self.content_changed()

    def clear_all(self):
        """Deselect all Items while leaving reference to model._checked intact"""
        self.model._checked.clear()
        # Inform Model about changes
        self.content_changed()


class BaseDict(QWidget):
    """A Widget to display a Dictionary

    Parameters
    ----------
    data : dict | None
        Input a pandas DataFrame with contents to display
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent

    """

    def __init__(self, data=None, parent=None):
        super().__init__(parent)

        self.model = BaseDictModel(data)
        self.view = QTableView()
        self.view.setModel(self.model)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

    def content_changed(self):
        """Informs ModelView about external change made in data
        """
        self.model.layoutChanged.emit()

    def replace_data(self, new_data):
        """Replaces model._data with new_data
        """
        self.model._data = new_data
        self.content_changed()


class EditDict(QWidget):
    """A Widget to display and edit a Dictionary

    Parameters
    ----------
    data : dict | None
        Input a pandas DataFrame with contents to display
    ui_buttons : bool
        If to display Buttons or not
    ui_button_pos: str
        The side on which to show the buttons, 'right', 'left', 'top' or 'bottom'
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent

    """

    def __init__(self, data=None, ui_buttons=True, ui_button_pos='right', parent=None):
        super().__init__(parent)
        self.ui_buttons = ui_buttons
        self.ui_button_pos = ui_button_pos

        self.model = EditDictModel(data)
        self.view = QTableView()
        self.view.setModel(self.model)

        self.init_ui()

    def init_ui(self):
        if self.ui_button_pos in ['top', 'bottom']:
            layout = QVBoxLayout()
            bt_layout = QHBoxLayout()
        else:
            layout = QHBoxLayout()
            bt_layout = QVBoxLayout()

        if self.ui_buttons:
            addrow_bt = QPushButton('Add')
            addrow_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            addrow_bt.clicked.connect(self.add_row)
            bt_layout.addWidget(addrow_bt)

            rmrow_bt = QPushButton('Remove')
            rmrow_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            rmrow_bt.clicked.connect(self.remove_row)
            bt_layout.addWidget(rmrow_bt)

            edit_bt = QPushButton('Edit')
            edit_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            edit_bt.clicked.connect(self.edit_item)
            bt_layout.addWidget(edit_bt)

            layout.addLayout(bt_layout)

        if self.ui_button_pos in ['top', 'left']:
            layout.addWidget(self.view)
        else:
            layout.insertWidget(0, self.view)

        self.setLayout(layout)

    def content_changed(self):
        """Informs ModelView about external change made in data
        """
        self.model.layoutChanged.emit()

    def replace_data(self, new_data):
        """Replaces model._data with new_data
        """
        self.model._data = new_data
        self.content_changed()

    def add_row(self):
        row = self.view.selectionModel().currentIndex().row()
        if row == -1:
            row = len(self.model._data)
        self.model.insertRow(row)

    def remove_row(self):
        row_idxs = set([idx.row() for idx in self.view.selectionModel().selectedIndexes()])
        for row_idx in row_idxs:
            self.model.removeRow(row_idx)

    def edit_item(self):
        self.view.edit(self.view.selectionModel().currentIndex())


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
    If you change the Reference to data outside of this class,
    give the changed DataFrame to replace_data to update this widget
    """

    def __init__(self, data=None, parent=None):
        super().__init__(parent)

        self.model = BasePandasModel(data)
        self.view = QTableView()
        self.view.setModel(self.model)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

    def content_changed(self):
        """Informs ModelView about external change made in data
        """
        self.model.layoutChanged.emit()

    def replace_data(self, new_data):
        """Replaces model._data with new_data
        """
        self.model._data = new_data
        self.content_changed()


class EditPandasTable(QWidget):
    """A Widget to display and edit a pandas DataFrame

    Parameters
    ----------
    data : pandas.DataFrame | None
        Input a pandas DataFrame with contents to display
    ui_buttons : bool
        If to display Buttons or not
    ui_button_pos: str
        The side on which to show the buttons, 'right', 'left', 'top' or 'bottom'
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent

    Notes
    -----
    If you change the Reference to data outside of this class,
    give the changed DataFrame to replace_data to update this widget
    """

    def __init__(self, data=pandas.DataFrame([]), ui_buttons=True, ui_button_pos='right', parent=None):
        super().__init__(parent)
        self.ui_buttons = ui_buttons
        self.ui_button_pos = ui_button_pos

        self.model = EditPandasModel(data)
        self.view = QTableView()
        self.view.setModel(self.model)

        self.rows_chkbx = QSpinBox()
        self.rows_chkbx.setMinimum(1)
        self.cols_chkbx = QSpinBox()
        self.cols_chkbx.setMinimum(1)

        self.init_ui()

    def init_ui(self):
        if self.ui_button_pos in ['top', 'bottom']:
            layout = QVBoxLayout()
            bt_layout = QHBoxLayout()
        else:
            layout = QHBoxLayout()
            bt_layout = QVBoxLayout()

        if self.ui_buttons:
            addr_layout = QHBoxLayout()
            addr_bt = QPushButton('Add Row')
            addr_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            addr_bt.clicked.connect(self.add_row)
            addr_layout.addWidget(addr_bt)
            addr_layout.addWidget(self.rows_chkbx)
            bt_layout.addLayout(addr_layout)

            addc_layout = QHBoxLayout()
            addc_bt = QPushButton('Add Column')
            addc_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            addc_bt.clicked.connect(self.add_column)
            addc_layout.addWidget(addc_bt)
            addc_layout.addWidget(self.cols_chkbx)
            bt_layout.addLayout(addc_layout)

            rmr_bt = QPushButton('Remove Row')
            rmr_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            rmr_bt.clicked.connect(self.remove_row)
            bt_layout.addWidget(rmr_bt)

            rmc_bt = QPushButton('Remove Column')
            rmc_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            rmc_bt.clicked.connect(self.remove_column)
            bt_layout.addWidget(rmc_bt)

            edit_bt = QPushButton('Edit')
            edit_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            edit_bt.clicked.connect(self.edit_item)
            bt_layout.addWidget(edit_bt)

            editrh_bt = QPushButton('Edit Row-Header')
            editrh_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            editrh_bt.clicked.connect(self.edit_row_header)
            bt_layout.addWidget(editrh_bt)

            editch_bt = QPushButton('Edit Column-Header')
            editch_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            editch_bt.clicked.connect(self.edit_col_header)
            bt_layout.addWidget(editch_bt)

            layout.addLayout(bt_layout)

        if self.ui_button_pos in ['top', 'left']:
            layout.addWidget(self.view)
        else:
            layout.insertWidget(0, self.view)

        self.setLayout(layout)

    def content_changed(self):
        """Informs ModelView about external change made in data
        """
        self.model.layoutChanged.emit()

    def update_data(self):
        """Has to be called, when model._data is rereferenced by for example add_row
        to keep external data updated

        Returns
        -------
        data : pandas.DataFrame
            The DataFrame of this widget

        Notes
        -----
        You can overwrite this function in a subclass e.g. to update an objects attribute
        (e.g. obj.data = self.model._data)
        """

        return self.model._data

    def replace_data(self, new_data):
        """Replaces model._data with new_data
        """
        self.model._data = new_data
        self.content_changed()

    def add_row(self):
        row = self.view.selectionModel().currentIndex().row()
        # Add row at the bottom if nothing is selected
        if row == -1 or len(self.view.selectionModel().selectedIndexes()) == 0:
            row = len(self.model._data.index)
        self.model.insertRows(row, self.rows_chkbx.value())
        self.update_data()

    def add_column(self):
        column = self.view.selectionModel().currentIndex().column()
        # Add column to the right if nothing is selected
        if column == -1 or len(self.view.selectionModel().selectedIndexes()) == 0:
            column = len(self.model._data.columns)
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
        old_value = self.model._data.index[row]
        text, ok = QInputDialog.getText(self, 'Change Row-Header', f'Change {old_value} in row {row} to:')
        if text and ok:
            self.model.setHeaderData(row, Qt.Vertical, text)

    def edit_col_header(self):
        column = self.view.selectionModel().currentIndex().column()
        old_value = self.model._data.columns[column]
        text, ok = QInputDialog.getText(self, 'Change Column-Header', f'Change {old_value} in column {column} to:')
        if text and ok:
            self.model.setHeaderData(column, Qt.Horizontal, text)


class AllBaseWidgets(QWidget):
    def __init__(self):
        super().__init__()

        self.exlist = ['Athena', 'Hephaistos', 'Zeus', 'Ares', 'Aphrodite', 'Poseidon']
        self.exdict = {'Athena': 231,
                       'Hephaistos': 44,
                       'Zeus': 'Boss',
                       'Ares': 'War'}
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
        # self.exdict = None

        self.widget_dict = {'BaseList': [self.exlist],
                            'EditList': [self.exlist],
                            'CheckList': [self.exlist, self.exchecked],
                            'BaseDict': [self.exdict],
                            'EditDict': [self.exdict],
                            'BasePandasTable': [self.expd],
                            'EditPandasTable': [self.expd]}

        self.tab_widget = QTabWidget()

        self.init_ui()

        self.setGeometry(0, 0, 800, 400)

    def init_ui(self):
        layout = QVBoxLayout()
        for widget in self.widget_dict:
            self.tab_widget.addTab(globals()[widget](*self.widget_dict[widget]), widget)

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    testw = AllBaseWidgets()
    testw.show()

    # Command-Line interrupt with Ctrl+C possible, easier debugging
    timer = QTimer()
    timer.timeout.connect(lambda: testw)
    timer.start(500)

    sys.exit(app.exec())
