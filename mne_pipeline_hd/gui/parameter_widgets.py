# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
Written on top of MNE-Python
Copyright © 2011-2020, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
"""
import sys
from ast import literal_eval
from decimal import Decimal
from functools import partial

import numpy as np
from PyQt5.QtCore import QSettings, QTimer, Qt
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QGridLayout, QGroupBox,
                             QHBoxLayout,
                             QLabel,
                             QLineEdit, QListWidget, QMainWindow, QPushButton, QScrollArea, QSizePolicy,
                             QSlider, QSpinBox, QVBoxLayout, QWidget)

from mne_pipeline_hd.gui.base_widgets import CheckList, EditDict, EditList


class Param(QWidget):
    """
    Base-Class Parameter-GUIs, not to be called directly
    Inherited Clases should have "Gui" in their name to get identified correctly
    """

    def __init__(self, data, param_name, param_alias=None, default=None, groupbox_layout=True,
                 none_select=False, description=None):
        """
        Parameters
        ----------
        data : dict | QMainWindow | QSettings
            The data-structure, in which the value of the parameter is stored
            (depends on the scenario how the Parameter-Widget is used,
             e.g. displaying parameters from Project or displaying Settings from Main-Window).
        param_name : str
            The name of the key, which stores the value in the data-structure.
        param_alias : str | None
            An optional alias-name for the parameter for display
            (if you want to use a name, which is more readable, but can't or shouldn't be used as a key in Python).
        default : object
            The default value depending on GUI-Type.
        groupbox_layout : bool
            If a groupbox should be used as layout (otherwise it is just a label)
        none_select : bool
            Set True if it should be possible to set the value to None by unchecking the GroupBox 
            (on the left of the name).
        description : str | None
            Supply an optional description for the parameter,
            which will displayed as a Tool-Tip when the mouse is hovered over the Widget.
        """

        super().__init__()
        self.data = data
        self.param_name = param_name
        if param_alias:
            self.param_alias = param_alias
        else:
            self.param_alias = self.param_name
        self.param_value = None
        self.default = default
        self.groupbox_layout = groupbox_layout
        self.none_select = none_select
        if description:
            self.setToolTip(description)
        self.param_unit = None

    def init_ui(self, layout):
        """Base layout initialization, which adds the given layout to a group-box with the parameters name"""

        main_layout = QVBoxLayout()

        if self.groupbox_layout:
            self.group_box = QGroupBox(self.param_alias)
            self.group_box.setLayout(layout)

            if self.none_select:
                self.group_box.setCheckable(True)
                self.group_box.toggled.connect(self.groupbox_toggled)

                if self.param_value is None:
                    self.group_box.setChecked(False)
                else:
                    self.group_box.setChecked(True)
            else:
                self.group_box.setCheckable(False)

            main_layout.addWidget(self.group_box)

        else:
            label_layout = QHBoxLayout()
            label_layout.addWidget(QLabel(self.param_alias))
            label_layout.addLayout(layout)
            main_layout.addLayout(label_layout)

        self.setLayout(main_layout)

    def init_h_layout(self):
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.param_widget)
        if self.param_unit:
            h_layout.addWidget(QLabel(self.param_unit))
        self.init_ui(h_layout)

    def groupbox_toggled(self, checked):
        if checked:
            self.get_param()
        else:
            self.param_value = None
        self.set_param()
        self.save_param()

    def check_groupbox_state(self):
        if self.none_select:
            if self.param_value is None:
                self.group_box.setChecked(False)
            else:
                self.group_box.setChecked(True)

    def read_param(self):
        # Make also usable by Main-Window-Settings
        if isinstance(self.data, dict):
            if self.param_name in self.data:
                value = self.data[self.param_name]
            else:
                value = self.default

        # Make also usable by QSettings
        elif isinstance(self.data, QSettings):
            if self.param_name in self.data.childKeys():
                value = self.data.value(self.param_name, defaultValue=self.default)
                # Convert booleans, which turn into strings with QSettings
                if value == "true":
                    value = True
                elif value == "false":
                    value = False
            else:
                value = self.default

        # Main usage to get data from Parameters in Project stored in MainWindow
        elif isinstance(self.data, QMainWindow):
            if self.param_name in self.data.pr.parameters[self.data.pr.p_preset]:
                value = self.data.pr.parameters[self.data.pr.p_preset][self.param_name]
            else:
                value = self.default

        else:
            value = self.default

        self.param_value = value

    def save_param(self):
        if isinstance(self.data, dict):
            self.data[self.param_name] = self.param_value
        elif isinstance(self.data, QSettings):
            self.data.setValue(self.param_name, self.param_value)
        elif isinstance(self.data, QMainWindow):
            self.data.pr.parameters[self.data.pr.p_preset][self.param_name] = self.param_value


class IntGui(Param):
    """A GUI for Integer-Parameters"""

    def __init__(self, data, param_name, param_alias=None, default=1, groupbox_layout=True, none_select=False,
                 description=None, param_unit=None, min_val=0, max_val=100, special_value_text=None):
        """
        Parameters
        ----------
        data : dict | QMainWindow | QSettings
            The data-structure, in which the value of the parameter is stored
            (depends on the scenario how the Parameter-Widget is used,
             e.g. displaying parameters from Project or displaying Settings from Main-Window).
        param_name : str
            The name of the key, which stores the value in the data-structure.
        param_alias : str | None
            An optional alias-name for the parameter for display
            (if you want to use a name, which is more readable, but can't or shouldn't be used as a key in Python).
        default : int | None
            The default value, if None defaults to 1.
        groupbox_layout : bool
            If a groupbox should be used as layout (otherwise it is just a label)
        none_select : bool
            Set True if it should be possible to set the value to None by unchecking the GroupBox
            (on the left of the name).
        description : str | None
            Supply an optional description for the parameter,
            which will displayed as a Tool-Tip when the mouse is hovered over the Widget.
        param_unit : str | None
            Supply an optional suffix with the name of the unit.
        min_val : int
            Set the minimumx value, defaults to 0.
        max_val : int
            Set the maximum value, defaults to 100.
        special_value_text : str | None
            Supply an optional text for the value 0.
        """

        super().__init__(data, param_name, param_alias, default, groupbox_layout, none_select, description)

        self.param_widget = QSpinBox()
        self.param_widget.setMinimum(min_val)
        self.param_widget.setMaximum(max_val)
        self.param_widget.setToolTip(f'MinValue = {min_val}\nMaxValue = {max_val}')
        if special_value_text:
            self.param_widget.setSpecialValueText(special_value_text)
        if param_unit:
            self.param_widget.setSuffix(f' {param_unit}')
        self.param_widget.valueChanged.connect(self.get_param)

        self.read_param()
        self.init_h_layout()
        self.set_param()
        self.save_param()

    def set_param(self):
        self.check_groupbox_state()
        if self.param_value is not None:
            self.param_widget.setValue(int(self.param_value))

    def get_param(self):
        self.param_value = self.param_widget.value()
        self.save_param()

        return self.param_value


class FloatGui(Param):
    """A GUI for Float-Parameters"""

    def __init__(self, data, param_name, param_alias=None, default=1., groupbox_layout=True, none_select=False,
                 description=None, param_unit=None, min_val=-100., max_val=100., step=0.1, decimals=2):
        """
        Parameters
        ----------
        data : dict | QMainWindow | QSettings
            The data-structure, in which the value of the parameter is stored
            (depends on the scenario how the Parameter-Widget is used,
             e.g. displaying parameters from Project or displaying Settings from Main-Window).
        param_name : str
            The name of the key, which stores the value in the data-structure.
        param_alias : str | None
            An optional alias-name for the parameter for display
            (if you want to use a name, which is more readable, but can't or shouldn't be used as a key in Python).
        default : float | None
            The default value, if None defaults to 1..
        groupbox_layout : bool
            If a groupbox should be used as layout (otherwise it is just a label)
        none_select : bool
            Set True if it should be possible to set the value to None by unchecking the GroupBox
            (on the left of the name).
        description : str | None
            Supply an optional description for the parameter,
            which will displayed as a Tool-Tip when the mouse is hovered over the Widget.
        param_unit : str | None
            Supply an optional suffix with the name of the unit.
        min_val : int | float
            Set the minimumx value, defaults to -100..
        max_val : int | float
            Set the maximum value, defaults to 100..
        step : int | float
            Set the step-size, defaults to 0.1.
        decimals : int
            Set the number of decimals of the value.
        """

        super().__init__(data, param_name, param_alias, default, groupbox_layout, none_select, description)
        self.param_widget = QDoubleSpinBox()
        self.param_widget.setMinimum(min_val)
        self.param_widget.setMaximum(max_val)
        self.param_widget.setSingleStep(step)
        self.param_widget.setDecimals(decimals)
        self.setToolTip(f'MinValue = {min_val}\nMaxVal = {max_val}')
        if param_unit:
            self.param_widget.setSuffix(f' {param_unit}')
        self.param_widget.valueChanged.connect(self.get_param)

        self.read_param()
        self.init_h_layout()
        self.set_param()
        self.save_param()

    def set_param(self):
        self.check_groupbox_state()
        if self.param_value is not None:
            self.param_widget.setValue(float(self.param_value))

    def get_param(self):
        self.param_value = self.param_widget.value()
        self.save_param()

        return self.param_value


class StringGui(Param):
    """
    A GUI for String-Parameters
    """

    def __init__(self, data, param_name, param_alias=None, default='Empty', groupbox_layout=True, none_select=False,
                 description=None, param_unit=None, input_mask=None):
        """

        Parameters
        ----------
        data : dict | QMainWindow | QSettings
            The data-structure, in which the value of the parameter is stored
            (depends on the scenario how the Parameter-Widget is used,
             e.g. displaying parameters from Project or displaying Settings from Main-Window).
        param_name : str
            The name of the key, which stores the value in the data-structure.
        param_alias : str | None
            An optional alias-name for the parameter for display
            (if you want to use a name, which is more readable, but can't or shouldn't be used as a key in Python).
        default : str | None
            The default value, if None defaults to 'Empty'
        groupbox_layout : bool
            If a groupbox should be used as layout (otherwise it is just a label)
        none_select : bool
            Set True if it should be possible to set the value to None by unchecking the GroupBox
            (on the left of the name).
        description : str | None
            Supply an optional description for the parameter,
            which will displayed as a Tool-Tip when the mouse is hovered over the Widget.
        param_unit : str | None
            Supply an optional suffix with the name of the unit.
        input_mask : str | None
            Define a string as in https://doc.qt.io/qt-5/qlineedit.html#inputMask-prop
        """

        super().__init__(data, param_name, param_alias, default, groupbox_layout, none_select, description)
        self.param_widget = QLineEdit()
        self.param_unit = param_unit
        if input_mask:
            self.param_widget.setInputMask(input_mask)
        self.param_widget.textChanged.connect(self.get_param)

        self.read_param()
        self.init_h_layout()
        self.set_param()
        self.save_param()

    def set_param(self):
        self.check_groupbox_state()
        if self.param_value is not None:
            self.param_widget.setText(self.param_value)

    def get_param(self):
        self.param_value = self.param_widget.text()
        self.save_param()

        return self.param_value


class FuncGui(Param):
    """A GUI for Parameters defined by small functions, e.g from numpy
    """

    def __init__(self, data, param_name, param_alias=None, default=None, groupbox_layout=True, none_select=False,
                 description=None, param_unit=None):
        """
        Parameters
        ----------
        data : dict | QMainWindow | QSettings
            The data-structure, in which the value of the parameter is stored
            (depends on the scenario how the Parameter-Widget is used,
             e.g. displaying parameters from Project or displaying Settings from Main-Window).
        param_name : str
            The name of the key, which stores the value in the data-structure.
        param_alias : str | None
            An optional alias-name for the parameter for display
            (if you want to use a name, which is more readable, but can't or shouldn't be used as a key in Python).
        default : str
            The default value, defaulting to None
        groupbox_layout : bool
            If a groupbox should be used as layout (otherwise it is just a label)
        none_select : bool
            Set True if it should be possible to set the value to None by unchecking the GroupBox
            (on the left of the name).
        description : str | None
            Supply an optional description for the parameter,
            which will displayed as a Tool-Tip when the mouse is hovered over the Widget.
        param_unit : str | None
            Supply an optional suffix with the name of the unit.
        """
        super().__init__(data, param_name, param_alias, default, groupbox_layout, none_select, description)
        self.param_exp = None
        self.param_widget = QLineEdit()
        self.param_unit = param_unit
        self.param_widget.setToolTip('Use of functions also allowed (from already imported modules + numpy as np)\n'
                                     'Be carefull as everything entered will be executed!')
        self.param_widget.editingFinished.connect(self.get_param)

        self.display_widget = QLabel()

        self.read_param()
        self.init_func_layout()
        self.set_param()
        self.save_param()

    def init_func_layout(self):
        func_layout = QGridLayout()
        label1 = QLabel('Insert Function/Value here')
        label2 = QLabel('Output')
        func_layout.addWidget(label1, 0, 0)
        func_layout.addWidget(label2, 0, 1, 1, 2)
        func_layout.addWidget(self.param_widget, 1, 0)
        func_layout.addWidget(self.display_widget, 1, 1)
        if self.param_unit:
            func_layout.addWidget(QLabel(self.param_unit))
        self.init_ui(func_layout)

    def set_param(self):
        self.check_groupbox_state()
        if self.param_value is not None:
            self.param_widget.setText(str(self.param_exp))
            self.display_widget.setText(str(self.param_value)[:20])

    def get_param(self):
        self.param_exp = self.param_widget.text()
        try:
            self.param_value = eval(self.param_exp, {'np': np})
            self.display_widget.setText(str(self.param_value)[:20])
        except (NameError, SyntaxError) as err:
            self.display_widget.setText(str(err)[:20])
            self.param_value = None
            return None
        else:
            self.save_param()
            return self.param_value

    def read_param(self):
        # Get not only param_value, but also param_exp storing the exact expression which is evaluated
        super().read_param()
        real_value = self.param_value
        self.param_name = self.param_name + '_exp'
        super().read_param()
        if str(self.param_value) == str(self.default):
            self.param_value = ''
        self.param_exp = self.param_value
        self.param_name = self.param_name[:-4]
        self.param_value = real_value

    def save_param(self):
        super().save_param()
        real_value = self.param_value
        self.param_name = self.param_name + '_exp'
        self.param_value = self.param_exp
        super().save_param()
        self.param_name = self.param_name[:-4]
        self.param_value = real_value


class BoolGui(Param):
    """A GUI for Boolean-Parameters"""

    def __init__(self, data, param_name, param_alias=None, default=False, groupbox_layout=False, none_select=False,
                 description=None, param_unit=None):
        """
        Parameters
        ----------
        data : dict | QMainWindow | QSettings
            The data-structure, in which the value of the parameter is stored
            (depends on the scenario how the Parameter-Widget is used,
             e.g. displaying parameters from Project or displaying Settings from Main-Window).
        param_name : str
            The name of the key, which stores the value in the data-structure.
        param_alias : str | None
            An optional alias-name for the parameter for display
            (if you want to use a name, which is more readable, but can't or shouldn't be used as a key in Python).
        default : object
            The default value, defaulting to False.
        groupbox_layout : bool
            If a groupbox should be used as layout (otherwise it is just a label)
        none_select : bool
            Set True if it should be possible to set the value to None by unchecking the GroupBox
            (on the left of the name).
        description : str | None
            Supply an optional description for the parameter,
            which will displayed as a Tool-Tip when the mouse is hovered over the Widget.
        param_unit : str | None
            Supply an optional suffix with the name of the unit.
        """
        super().__init__(data, param_name, param_alias, default, groupbox_layout, none_select, description)
        self.param_unit = param_unit
        self.param_widget = QCheckBox()
        self.param_widget.toggled.connect(self.get_param)

        self.read_param()
        self.init_h_layout()
        self.set_param()
        self.save_param()

    def set_param(self):
        if self.param_value is not None:
            if self.param_value:
                self.param_widget.setChecked(True)
            else:
                self.param_widget.setChecked(False)

    def get_param(self):
        if self.param_widget.isChecked():
            self.param_value = True
        else:
            self.param_value = False
        self.save_param()

        return self.param_value


class TupleGui(Param):
    """A GUI for Tuple-Parameters"""

    def __init__(self, data, param_name, param_alias=None, default=None, groupbox_layout=True, none_select=False,
                 description=None, param_unit=None, min_val=-1000., max_val=1000., step=.1, decimals=2):
        """
        Parameters
        ----------
        data : dict | QMainWindow | QSettings
            The data-structure, in which the value of the parameter is stored
            (depends on the scenario how the Parameter-Widget is used,
             e.g. displaying parameters from Project or displaying Settings from Main-Window).
        param_name : str
            The name of the key, which stores the value in the data-structure.
        param_alias : str | None
            An optional alias-name for the parameter for display
            (if you want to use a name, which is more readable, but can't or shouldn't be used as a key in Python).
        default : object
            The default value, defaulting to (0, 1).
        groupbox_layout : bool
            If a groupbox should be used as layout (otherwise it is just a label)
        none_select : bool
            Set True if it should be possible to set the value to None by unchecking the GroupBox
            (on the left of the name).
        description : str | None
            Supply an optional description for the parameter,
            which will displayed as a Tool-Tip when the mouse is hovered over the Widget.
        param_unit : str | None
            Supply an optional suffix with the name of the unit.
        min_val : int | float
            Set the minimumx value, defaults to -100..
        max_val : int | float
            Set the maximum value, defaults to 100..
        step : int | float
            Set the amount, one step takes
        decimals : int
            Set the number of decimals of the value
        """
        if default is None:
            default = (0, 1)

        super().__init__(data, param_name, param_alias, default, groupbox_layout, none_select, description)

        self.setToolTip(f'MinValue = {min_val}\nMaxVal = {max_val}\nStep = {step}\nDecimals = {decimals}')

        self.param_widget1 = QDoubleSpinBox()
        self.param_widget1.setMinimum(min_val)
        self.param_widget1.setMaximum(max_val)
        self.param_widget1.setSingleStep(step)
        self.param_widget1.setDecimals(decimals)
        if param_unit:
            self.param_widget1.setSuffix(f' {param_unit}')
        self.param_widget1.valueChanged.connect(self.get_param)

        self.param_widget2 = QDoubleSpinBox()
        self.param_widget2.setMinimum(min_val)
        self.param_widget2.setMaximum(max_val)
        self.param_widget2.setSingleStep(step)
        self.param_widget2.setDecimals(decimals)
        if param_unit:
            self.param_widget2.setSuffix(f' {param_unit}')
        self.param_widget2.valueChanged.connect(self.get_param)

        self.read_param()
        self.init_tuple_layout()
        self.set_param()
        self.save_param()

    def init_tuple_layout(self):
        tuple_layout = QHBoxLayout()
        tuple_layout.addWidget(self.param_widget1)
        tuple_layout.addWidget(self.param_widget2)
        self.init_ui(tuple_layout)

    def set_param(self):
        # Signal valueChanged is already emitted after first setValue,
        # which leads to second param_value being 0 without being preserved in self.loaded_value
        self.check_groupbox_state()
        if self.param_value is not None:
            self.loaded_value = self.param_value
            self.param_widget1.setValue(self.loaded_value[0])
            self.param_widget2.setValue(self.loaded_value[1])

    def get_param(self):
        self.param_value = (self.param_widget1.value(), self.param_widget2.value())
        self.save_param()

        return self.param_value


class ComboGui(Param):
    """A GUI for a Parameter with limited options"""

    def __init__(self, data, param_name, options, param_alias=None, default=object(), groupbox_layout=True,
                 none_select=False, description=None, param_unit=None):
        """
        Parameters
        ----------
        data : dict | QMainWindow | QSettings
            The data-structure, in which the value of the parameter is stored
            (depends on the scenario how the Parameter-Widget is used,
             e.g. displaying parameters from Project or displaying Settings from Main-Window).
        param_name : str
            The name of the key, which stores the value in the data-structure.
        param_alias : str | None
            An optional alias-name for the parameter for display
            (if you want to use a name, which is more readable, but can't or shouldn't be used as a key in Python).
        default : object
            The default value, defaulting to an empty object
        groupbox_layout : bool
            If a groupbox should be used as layout (otherwise it is just a label)
        none_select : bool
            Set True if it should be possible to set the value to None by unchecking the GroupBox
            (on the left of the name).
        description : str | None
            Supply an optional description for the parameter,
            which will displayed as a Tool-Tip when the mouse is hovered over the Widget.
        param_unit : str | None
            Supply an optional suffix with the name of the unit.
        """
        super().__init__(data, param_name, param_alias, default, groupbox_layout, none_select, description)
        self.options = options
        self.param_widget = QComboBox()
        self.param_widget.activated.connect(self.get_param)
        self.param_unit = param_unit
        for option in self.options:
            self.param_widget.addItem(str(option))

        self.read_param()
        self.init_h_layout()
        self.set_param()
        self.save_param()

    def set_param(self):
        self.check_groupbox_state()
        if self.param_value is not None:
            self.param_widget.setCurrentText(str(self.param_value))

    def get_param(self):
        try:
            self.param_value = literal_eval(self.param_widget.currentText())
        except (SyntaxError, ValueError):
            self.param_value = self.param_widget.currentText()
        self.save_param()

        return self.param_value


class ListDialog(QDialog):
    def __init__(self, paramw):
        super().__init__(paramw)
        self.paramw = paramw

        self.init_layout()
        self.open()

    def init_layout(self):
        layout = QVBoxLayout()
        layout.addWidget(EditList(self.paramw.param_value))
        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)
        self.setLayout(layout)

    def closeEvent(self, event):
        self.paramw.set_param()
        self.paramw.save_param()
        event.accept()


class ListGui(Param):
    """A GUI for as list"""

    def __init__(self, data, param_name, param_alias=None, default=None, groupbox_layout=True, none_select=False,
                 description=None, param_unit=None, value_string_length=30):
        """
        Parameters
        ----------
        data : dict | QMainWindow | QSettings
            The data-structure, in which the value of the parameter is stored
            (depends on the scenario how the Parameter-Widget is used,
             e.g. displaying parameters from Project or displaying Settings from Main-Window).
        param_name : str
            The name of the key, which stores the value in the data-structure.
        param_alias : str | None
            An optional alias-name for the parameter for display
            (if you want to use a name, which is more readable, but can't or shouldn't be used as a key in Python).
        default : object
            The default value, defaulting to None
        groupbox_layout : bool
            If a groupbox should be used as layout (otherwise it is just a label)
        none_select : bool
            Set True if it should be possible to set the value to None by unchecking the GroupBox
            (on the left of the name).
        description : str | None
            Supply an optional description for the parameter,
            which will displayed as a Tool-Tip when the mouse is hovered over the Widget.
        param_unit : str | None
            Supply an optional suffix with the name of the unit.
        value_string_length : int | None
            Set the limit of characters to which the value converted to a string will be displayed
        """

        default = default or list()

        super().__init__(data, param_name, param_alias, default, groupbox_layout, none_select, description)
        self.param_unit = param_unit
        self.value_string_length = value_string_length
        # Cache param_value to use after
        self.cached_value = None

        self.read_param()
        self.init_layout()
        self.set_param()
        self.save_param()

    def init_layout(self):
        list_layout = QHBoxLayout()

        self.value_label = QLabel()
        list_layout.addWidget(self.value_label)

        self.param_widget = QPushButton('Edit')
        self.param_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.param_widget.clicked.connect(partial(ListDialog, self))
        list_layout.addWidget(self.param_widget, alignment=Qt.AlignCenter)

        self.init_ui(list_layout)

    def set_param(self):
        if self.param_value is not None:
            self.cached_value = self.param_value
        self.check_groupbox_state()
        if self.param_value is not None:
            if self.param_unit:
                val_str = ', '.join([f'{item} {self.param_unit}' for item in self.param_value])
            else:
                val_str = ', '.join([str(item) for item in self.param_value])
            if len(val_str) >= self.value_string_length:
                self.value_label.setText(f'{val_str[:self.value_string_length]} ...')
            else:
                self.value_label.setText(val_str)
        else:
            self.value_label.setText('None')

    def get_param(self):
        if self.group_box.isChecked() and self.param_value is None:
            if self.cached_value:
                self.param_value = self.cached_value
            else:
                self.param_value = list()
            self.value_label.clear()
        self.save_param()

        return self.param_value


class CheckListDialog(QDialog):
    def __init__(self, paramw):
        super().__init__(paramw)
        self.paramw = paramw

        self.init_layout()
        self.open()

    def init_layout(self):
        layout = QVBoxLayout()
        layout.addWidget(CheckList(data=self.paramw.options, checked=self.paramw.param_value,
                                   one_check=self.paramw.one_check))

        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)

    def closeEvent(self, event):
        self.paramw.set_param()
        self.paramw.save_param()
        event.accept()


class CheckListGui(Param):
    """A GUI to select items from a list of options
    """

    def __init__(self, data, param_name, options, param_alias=None, default=None, groupbox_layout=True,
                 none_select=False, description=None, param_unit=None, value_string_length=30, one_check=False):
        """
        Parameters
        ----------
        data : dict | QMainWindow | QSettings
            The data-structure, in which the value of the parameter is stored
            (depends on the scenario how the Parameter-Widget is used,
             e.g. displaying parameters from Project or displaying Settings from Main-Window).
        param_name : str
            The name of the key, which stores the value in the data-structure.
        options : list
            The items from which to choose
        param_alias : str | None
            An optional alias-name for the parameter for display
            (if you want to use a name, which is more readable, but can't or shouldn't be used as a key in Python).
        default : int | None
            The default value, if None defaults to 1.
        groupbox_layout : bool
            If a groupbox should be used as layout (otherwise it is just a label)
        none_select : bool
            Set True if it should be possible to set the value to None by unchecking the GroupBox
            (on the left of the name).
        description : str | None
            Supply an optional description for the parameter,
            which will displayed as a Tool-Tip when the mouse is hovered over the Widget.
        param_unit : str | None
            Supply an optional suffix with the name of the unit.
        value_string_length : int | None
            Set the limit of characters to which the value converted to a string will be displayed
        one_check : bool
            Set to True, if only one item should be selectable (or use ComboGUI)
        """

        if not isinstance(options, list) or len(options) == 0:
            options = ['Empty']
            default = 'Empty'

        super().__init__(data, param_name, param_alias, default, groupbox_layout, none_select, description)
        self.options = options
        self.param_unit = param_unit
        self.value_string_length = value_string_length
        self.one_check = one_check
        # Cache param_value to use after
        self.cached_value = None

        self.read_param()
        self.init_layout()
        self.set_param()
        self.save_param()

    def init_layout(self):
        check_list_layout = QVBoxLayout()

        self.param_widget = QPushButton('Edit')
        self.param_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.param_widget.clicked.connect(partial(CheckListDialog, self))
        check_list_layout.addWidget(self.param_widget)

        self.value_label = QLabel()
        check_list_layout.addWidget(self.value_label)
        self.init_ui(check_list_layout)

    def set_param(self):
        if self.param_value is not None:
            self.cached_value = self.param_value
        self.check_groupbox_state()
        if self.param_value is not None:
            if self.param_unit:
                val_str = ', '.join([f'{item} {self.param_unit}' for item in self.param_value])
            else:
                val_str = ', '.join([str(item) for item in self.param_value])
            if len(val_str) >= self.value_string_length:
                self.value_label.setText(f'{val_str[:self.value_string_length]} ...')
            else:
                self.value_label.setText(val_str)
        else:
            self.value_label.setText('None')

    def get_param(self):
        if self.group_box.isChecked() and self.param_value is None:
            if self.cached_value:
                self.param_value = self.cached_value
            else:
                self.param_value = list()
            self.value_label.clear()
        self.save_param()

        return self.param_value


class DictDialog(QDialog):
    def __init__(self, paramw):
        super().__init__(paramw)
        self.paramw = paramw

        self.init_layout()
        self.open()

    def init_layout(self):
        layout = QVBoxLayout()
        layout.addWidget(EditDict(self.paramw.param_value))
        close_bt = QPushButton('Close')
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)
        self.setLayout(layout)

    def closeEvent(self, event):
        self.paramw.set_param()
        self.paramw.save_param()
        event.accept()


class DictGui(Param):
    """A GUI for a dictionary"""

    def __init__(self, data, param_name, param_alias=None, default=None, groupbox_layout=True, none_select=False,
                 description=None, param_unit=None, value_string_length=30):
        """
        
        Parameters
        ----------
        data : dict | QMainWindow | QSettings
            The data-structure, in which the value of the parameter is stored
            (depends on the scenario how the Parameter-Widget is used,
             e.g. displaying parameters from Project or displaying Settings from Main-Window).
        param_name : str
            The name of the key, which stores the value in the data-structure.
        param_alias : str | None
            An optional alias-name for the parameter for display
            (if you want to use a name, which is more readable, but can't or shouldn't be used as a key in Python).
        default : int | None
            The default value, if None defaults to an empty dict.
        groupbox_layout : bool
            If a groupbox should be used as layout (otherwise it is just a label)
        none_select : bool
            Set True if it should be possible to set the value to None by unchecking the GroupBox
            (on the left of the name).
        description : str | None
            Supply an optional description for the parameter,
            which will displayed as a Tool-Tip when the mouse is hovered over the Widget.
        param_unit : str | None
            Supply an optional suffix with the name of the unit.
        value_string_length : int | None
            Set the limit of characters to which the value converted to a string will be displayed
        """

        default = default or dict()

        super().__init__(data, param_name, param_alias, default, groupbox_layout, none_select, description)
        self.param_unit = param_unit
        self.value_string_length = value_string_length
        # Cache param_value to use after setting param_value to None with GroupBox-Checkbox
        self.cached_value = None

        self.read_param()
        self.init_layout()
        self.set_param()
        self.save_param()

    def init_layout(self):
        dict_layout = QHBoxLayout()

        self.param_widget = QPushButton('Edit')
        self.param_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.param_widget.clicked.connect(partial(DictDialog, self))
        dict_layout.addWidget(self.param_widget)

        self.value_label = QLabel()
        dict_layout.addWidget(self.value_label)

        self.init_ui(dict_layout)

    def set_param(self):
        if self.param_value is not None:
            self.cached_value = self.param_value
        self.check_groupbox_state()
        if self.param_value is not None:
            if self.param_unit:
                val_str = ', '.join([f'{key} {self.param_unit}: {value} {self.param_unit}'
                                     for key, value in self.param_value.items()])
            else:
                val_str = ', '.join([f'{key}: {value}' for key, value in self.param_value.items()])
            if len(val_str) > self.value_string_length:
                self.value_label.setText(f'{val_str[:self.value_string_length]} ...')
            else:
                self.value_label.setText(val_str)
        else:
            self.value_label.setText('None')

    def get_param(self):
        if self.group_box.isChecked() and self.param_value is None:
            if self.cached_value:
                self.param_value = self.cached_value
            else:
                self.param_value = dict()
            self.value_label.clear()
        self.save_param()

        return self.param_value


class SliderGui(Param):
    """A GUI to show a slider for Int/Float-Parameters"""

    def __init__(self, data, param_name, param_alias=None, default=1, groupbox_layout=True, none_select=False,
                 description=None, param_unit=None, min_val=0, max_val=100, step=1):
        """
        Parameters
        ----------
        data : dict | QMainWindow | QSettings
            The data-structure, in which the value of the parameter is stored
            (depends on the scenario how the Parameter-Widget is used,
             e.g. displaying parameters from Project or displaying Settings from Main-Window).
        param_name : str
            The name of the key, which stores the value in the data-structure.
        param_alias : str | None
            An optional alias-name for the parameter for display
            (if you want to use a name, which is more readable, but can't or shouldn't be used as a key in Python).
        default : int | None
            The default value, if None defaults to 1.
        groupbox_layout : bool
            If a groupbox should be used as layout (otherwise it is just a label)
        none_select : bool
            Set True if it should be possible to set the value to None by unchecking the GroupBox
            (on the left of the name).
        description : str | None
            Supply an optional description for the parameter,
            which will displayed as a Tool-Tip when the mouse is hovered over the Widget.
        param_unit : str | None
            Supply an optional suffix with the name of the unit.
        min_val : int | float
            Set the minimumx value, defaults to 0.
        max_val : int | float
            Set the maximum value, defaults to 100..
        step : int | float
            Set the step-size, defaults to 1.
        """
        super().__init__(data, param_name, param_alias, default, groupbox_layout, none_select, description)
        self.min_val = min_val
        self.max_val = max_val
        self.param_widget = QSlider()
        self.param_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.param_unit = param_unit
        self.decimal_count = max([abs(Decimal(str(value)).as_tuple().exponent) for value in (min_val, max_val)])
        if self.decimal_count > 0:
            self.param_widget.setMinimum(int(self.min_val * 10 ** self.decimal_count))
            self.param_widget.setMaximum(int(self.max_val * 10 ** self.decimal_count))
        else:
            self.param_widget.setMinimum(self.min_val)
            self.param_widget.setMaximum(self.max_val)
        self.param_widget.setSingleStep(int(step))
        self.param_widget.setOrientation(Qt.Horizontal)
        self.param_widget.setTracking(True)
        self.param_widget.setToolTip(f'MinValue = {min_val}\nMaxValue = {max_val}\nStep = {step}')
        self.param_widget.valueChanged.connect(self.get_param)

        self.display_widget = QLineEdit()
        self.display_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.display_widget.setAlignment(Qt.AlignRight)
        self.display_widget.editingFinished.connect(self.display_edited)

        self.read_param()
        self.init_slider_ui()
        self.set_param()
        self.save_param()

    def init_slider_ui(self):
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self.param_widget, stretch=10)
        slider_layout.addWidget(self.display_widget, stretch=1)
        if self.param_unit:
            slider_layout.addWidget(QLabel(self.param_unit))

        self.init_ui(slider_layout)

    def display_edited(self):
        try:
            new_value = literal_eval(self.display_widget.text())
        except (ValueError, SyntaxError):
            new_value = ''
        if isinstance(new_value, int):
            self.param_value = new_value
            self.decimal_count = 0
            self.param_widget.setMinimum(self.min_val)
            self.param_widget.setMaximum(self.max_val)
            self.param_widget.setValue(self.param_value)
        elif isinstance(new_value, float):
            new_decimal_count = abs(Decimal(str(new_value)).as_tuple().exponent)
            if new_decimal_count > 0 and new_decimal_count != self.decimal_count:
                self.decimal_count = new_decimal_count
                self.param_widget.setMinimum(self.min_val * 10 ** self.decimal_count)
                self.param_widget.setMaximum(self.max_val * 10 ** self.decimal_count)
            self.param_value = new_value
            self.param_widget.setValue(int(new_value * 10 ** self.decimal_count))

    def set_param(self):
        self.check_groupbox_state()
        if self.param_value is not None:
            if self.decimal_count > 0:
                self.param_widget.setValue(int(self.param_value * 10 ** self.decimal_count))
            else:
                self.param_widget.setValue(self.param_value)
            self.display_widget.setText(str(self.param_value))

    def get_param(self):
        new_value = self.param_widget.value()
        if self.decimal_count > 0:
            new_value /= 10 ** self.decimal_count
        self.param_value = new_value
        self.display_widget.setText(str(self.param_value))
        self.save_param()

        return self.param_value


# Todo: Label-GUI
class LabelGui(Param):
    """A GUI to select Labels depending on parcellation"""

    def __init__(self, data, param_name, param_alias=None, default=None, none_select=False, description=None):
        super().__init__(data, param_name, param_alias, default, none_select, description)
        self.param_name = param_name
        self.param_value = []
        self.param_widget = QListWidget()
        self.param_widget.itemChanged.connect(self.get_param)

        self.read_param()
        self.init_label_ui()
        self.set_param()
        self.save_param()

    def init_label_ui(self):
        label_layout = QVBoxLayout()
        start_bt = QPushButton('Select Labels')
        label_layout.addWidget(start_bt)

        self.init_ui(label_layout)

    def set_param(self):
        pass

    def get_param(self):
        pass
        self.save_param()

        return self.param_value


if __name__ == '__main__':
    app = QApplication(sys.argv)
    scroll_area = QScrollArea()
    sub_layout = QGridLayout()
    main_win = QWidget()

    parameters = {'TestInt': None,
                  'TestList': [1, 454.33, 'post_central-lh', 'raga', 5],
                  'TextDict': {'A': 'hubi', 'B': 58.144, 3: 'post_lh'},
                  'Fugi?': True,
                  'TestFloat': 5.3,
                  'TestString': 'Havona',
                  'TestSlider': 5,
                  'TestSlider2': 4.5,
                  'TestFunc': 5000,
                  'TestTuple': (45, 6.5),
                  'TestCombo': 'a',
                  'TestCheckList': ['bananaaa']}

    a = IntGui(parameters, 'TestInt', min_val=-4, max_val=10, param_unit='t', none_select=True, description='Test')
    b = ListGui(parameters, 'TestList', param_unit='a', none_select=True, description='Test')
    c = DictGui(parameters, 'TextDict', param_unit='a', none_select=True, description='Test')
    d = BoolGui(parameters, 'Huba?', param_unit='a', none_select=True, description='Test')
    e = FloatGui(parameters, 'TestFloat', min_val=-18, max_val=+64, step=0.4, decimals=6, param_unit='flurbo',
                 none_select=True, description='Test')
    f = StringGui(parameters, 'TestString', input_mask='ppAAA.AA;_', param_unit='a', none_select=True,
                  description='Test')
    g = SliderGui(parameters, 'TestSlider', min_val=-10, max_val=10, step=1, param_unit='Hz', none_select=True,
                  description='Test')
    h = SliderGui(parameters, 'TestSlider2', min_val=0, max_val=20.258, step=5, param_unit='Fz', none_select=True,
                  description='Test')
    i = FuncGui(parameters, 'TestFunc', param_unit='a', none_select=True, description='Test')
    j = TupleGui(parameters, 'TestTuple', min_val=-10, max_val=20, step=1, decimals=3, param_unit='a', none_select=True,
                 description='Test')
    k = ComboGui(parameters, 'TestCombo', options=['a', 'b', 'c'], param_unit='a', none_select=True, description='Test')
    l = CheckListGui(parameters, 'TestCheckList', options=['lemon', 'pineapple', 'bananaaa'], param_unit='a',
                     none_select=True, description='Test')
    m = StringGui(parameters, 'TestString2', description='Test')
    sub_layout.addWidget(a, 0, 0)
    sub_layout.addWidget(b, 0, 1)
    sub_layout.addWidget(c, 0, 2)
    sub_layout.addWidget(d, 0, 3)
    sub_layout.addWidget(e, 0, 4)
    sub_layout.addWidget(f, 1, 0)
    sub_layout.addWidget(g, 1, 1)
    sub_layout.addWidget(h, 1, 2)
    sub_layout.addWidget(i, 1, 3)
    sub_layout.addWidget(j, 1, 4)
    sub_layout.addWidget(k, 2, 0)
    sub_layout.addWidget(l, 2, 1)
    sub_layout.addWidget(m, 2, 2)
    main_win.setLayout(sub_layout)
    scroll_area.setWidget(main_win)
    scroll_area.show()

    # Command-Line interrupt with Ctrl+C possible, easier debugging
    timer = QTimer()
    timer.timeout.connect(lambda: parameters)
    timer.start(500)

    sys.exit(app.exec())
