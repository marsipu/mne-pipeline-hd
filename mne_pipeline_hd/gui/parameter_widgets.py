# -*- coding: utf-8 -*-
"""
Authors: Martin Schulz <dev@mgschulz.de>
License: BSD 3-Clause
Github: https://github.com/marsipu/mne-pipeline-hd
"""
from ast import literal_eval
from functools import partial

import mne
import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QDockWidget,
    QTabWidget,
    QScrollArea,
    QMessageBox,
    QColorDialog,
)
from mne_qt_browser._pg_figure import _get_color
from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkRenderingCore import vtkCellPicker

from mne_pipeline_hd import _object_refs
from mne_pipeline_hd.gui.base_widgets import (
    CheckList,
    EditDict,
    EditList,
    SimpleList,
    SimpleDialog,
    ComboBox,
)
from mne_pipeline_hd.gui.dialogs import CheckListDlg
from mne_pipeline_hd.gui.gui_utils import (
    get_std_icon,
    WorkerDialog,
    get_exception_tuple,
    get_user_input_string,
    center,
)
from mne_pipeline_hd.pipeline.controller import Controller
from mne_pipeline_hd.pipeline.loading import FSMRI
from mne_pipeline_hd.pipeline.pipeline_utils import QS, iswin


class Param(QWidget):
    """
    Base-Class Parameter-GUIs, not to be called directly
    Inherited Clases should have "Gui" in their name to get
    identified correctly.

    Attributes
    ----------
    paramChanged : pyqtSignal
        This signal is emmited when the parameter changes.
    """

    paramChanged = pyqtSignal(object)

    def __init__(
        self,
        data,
        name,
        alias=None,
        default=None,
        param_unit=None,
        groupbox_layout=True,
        none_select=False,
        description=None,
        depending_on=None,
    ):
        """
        Parameters
        ----------
        data : dict | Controller | QSettings
            The data-structure, in which the value of the parameter is stored
            (depends on the scenario how the Parameter-Widget is used,
             e.g. displaying parameters from Project or displaying Settings
             from Main-Window).
        name : str
            The name of the key, which stores the value in the data-structure.
        alias : str | None
            An optional alias-name for the parameter for display
            (if you want to use a name, which is more readable, but can't or
            shouldn't be used as a key in Python).
        default : object
            The default value depending on GUI-Type.
        param_unit : str | None
            Supply an optional suffix with the name of the unit.
        groupbox_layout : bool
            If a groupbox should be used as layout
            (otherwise it is just a label), if None no label
        none_select : bool
            Set True if it should be possible to set the value to None
            by unchecking the GroupBox (on the left of the name).
        description : str | None
            Supply an optional description for the parameter,
            which will displayed as a Tool-Tip when the mouse
            is hovered over the Widget.
        depending_on : str | None
            Supply the name of another Paramter here and connect it
             to this widget.
        """

        super().__init__()
        self.data = data
        self.name = name
        if alias is not None:
            self.alias = alias
        else:
            self.alias = self.name
        self.param_value = None
        self.default = default
        self.param_unit = param_unit
        self.groupbox_layout = groupbox_layout
        self.none_select = none_select
        self.description = description
        if self.description:
            self.setToolTip(description)

        # Making sure, that groupbox_layout is on when none_select is one
        # (Selection of None works by checking/unchecking the GroupBox)
        if self.none_select:
            self.groupbox_layout = True

        # Connect widget on which this widget depends on
        dep_widget = _object_refs["parameter_widgets"].get(depending_on, None)
        if dep_widget is not None:
            dep_widget.paramChanged.connect(self.set_param)

        # Add to object-reference
        _object_refs["parameter_widgets"][self.name] = self

    def init_ui(self, layout=None):
        """Base layout initialization, which adds the given layout to a
        group-box with the parameters name if groupbox_layout is enabled.
        Else the layout will be horizontal with a QLabel for the name"""

        main_layout = QHBoxLayout()

        if self.groupbox_layout:
            self.group_box = QGroupBox(self.alias)
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
            # Add this to get no label in MultiTypeGui
            if self.alias != "":
                main_layout.addWidget(QLabel(self.alias))
            main_layout.addLayout(layout)

        self.setLayout(main_layout)

    def groupbox_toggled(self, checked):
        if checked:
            self._get_param()
        else:
            self.param_value = None
        self._set_param()
        self.save_param()

    def check_groupbox_state(self):
        if self.none_select:
            if self.param_value is None:
                self.group_box.setChecked(False)
            else:
                # Save param_value separatetly, because when Widget inside
                # GroupBox changes Enabled-State to Enabled,
                # the get_param-method may be invoked leading to rewriting
                # param_value with the displayed value and not with the
                # original value.
                saved_value = self.param_value
                self.group_box.setChecked(True)
                self.param_value = saved_value
                self.save_param()

    def get_value(self):
        """This should be implemented for each widget"""
        pass

    def _get_param(self):
        """Get current parameter value from gui."""
        self.param_value = self.get_value()
        self.paramChanged.emit(self.param_value)
        self.save_param()

    def _set_param(self):
        """Set current parameter value to gui."""
        self.check_groupbox_state()
        if self.param_value is not None:
            self.set_value(self.param_value)

    def set_param(self, value):
        """Set parameter externally to gui and parameters."""
        self.param_value = value
        self._set_param()
        if value is not None:
            # Read from widget to get value e.g. inside min/max-bounds
            self._get_param()

    def _read_data(self, name):
        # get data from dictionary
        if isinstance(self.data, dict):
            if name in self.data:
                value = self.data[name]
            else:
                value = self.default

        # get data from Parameters in Project in MainWindow
        # (depending on selected parameter-preset and selected Project)
        elif isinstance(self.data, Controller):
            if name in self.data.pr.parameters[self.data.pr.p_preset]:
                value = self.data.pr.parameters[self.data.pr.p_preset][name]
            else:
                value = self.default

        # get data from QSettings
        elif isinstance(self.data, QS):
            if name in self.data.childKeys():
                value = self.data.value(name)
            else:
                value = self.default

        return value

    def read_param(self):
        self.param_value = self._read_data(self.name)

    def _save_data(self, name, value):
        if isinstance(self.data, dict):
            self.data[name] = value
        elif isinstance(self.data, Controller):
            self.data.pr.parameters[self.data.pr.p_preset][name] = value
        elif isinstance(self.data, QS):
            self.data.setValue(name, value)

    def save_param(self):
        self._save_data(self.name, self.param_value)

    def copy_widget(self):
        """Return a copy of this widget"""
        return


class IntGui(Param):
    """A GUI for Integer-Parameters"""

    def __init__(self, min_val=0, max_val=1000, special_value_text=None, **kwargs):
        """
        Parameters
        ----------
        min_val : int
            Set the minimumx value, defaults to 0.
        max_val : int
            Set the maximum value, defaults to 100.
        special_value_text : str | None
            Supply an optional text for the value 0.
        **kwargs
            All the parameters fo :method:`~Param.__init__` go here.
        """

        super().__init__(**kwargs)

        self.param_widget = QSpinBox()
        self.param_widget.setMinimum(min_val)
        self.param_widget.setMaximum(max_val)
        self.param_widget.setToolTip(f"MinValue = {min_val}\nMaxValue = {max_val}")
        if special_value_text:
            self.param_widget.setSpecialValueText(special_value_text)
        if self.param_unit:
            self.param_widget.setSuffix(f" {self.param_unit}")
        self.param_widget.valueChanged.connect(self._get_param)

        self.read_param()
        self._init_layout()
        self._set_param()
        self.save_param()

    def _init_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self.param_widget)
        self.init_ui(layout)

    def set_value(self, value):
        self.param_widget.setValue(int(value))

    def get_value(self):
        return self.param_widget.value()


class FloatGui(Param):
    """A GUI for Float-Parameters"""

    def __init__(self, min_val=-1000.0, max_val=1000.0, step=0.1, decimals=2, **kwargs):
        """
        Parameters
        ----------
        min_val : int | float
            Set the minimumx value, defaults to -100..
        max_val : int | float
            Set the maximum value, defaults to 100..
        step : int | float
            Set the step-size, defaults to 0.1.
        decimals : int
            Set the number of decimals of the value.
        **kwargs
            All the parameters fo :method:`~Param.__init__` go here.
        """

        super().__init__(**kwargs)
        self.param_widget = QDoubleSpinBox()
        self.param_widget.setMinimum(min_val)
        self.param_widget.setMaximum(max_val)
        self.param_widget.setSingleStep(step)
        self.param_widget.setDecimals(decimals)
        self.param_widget.setToolTip(f"MinValue = {min_val}\nMaxVal = {max_val}")
        if self.param_unit:
            self.param_widget.setSuffix(f" {self.param_unit}")
        self.param_widget.valueChanged.connect(self._get_param)

        self.read_param()
        self._init_layout()
        self._set_param()
        self.save_param()

    def _init_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self.param_widget)
        self.init_ui(layout)

    def set_value(self, value):
        self.param_widget.setValue(float(value))

    def get_value(self):
        return self.param_widget.value()


class StringGui(Param):
    """
    A GUI for String-Parameters
    """

    def __init__(self, **kwargs):
        """

        Parameters
        ----------
        **kwargs
            All the parameters fo :method:`~Param.__init__` go here.
        """

        super().__init__(**kwargs)
        self.param_widget = QLineEdit()
        self.param_widget.textChanged.connect(self._get_param)

        self.read_param()
        self._init_layout()
        self._set_param()
        self.save_param()

    def _init_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self.param_widget)
        if self.param_unit is not None:
            layout.addWidget(QLabel(self.param_unit))
        self.init_ui(layout)

    def set_value(self, value):
        self.param_widget.setText(value)

    def get_value(self):
        return self.param_widget.text()


def _eval_param(param_exp):
    try:
        return eval(param_exp, {"np": np})
    except (NameError, SyntaxError, ValueError, TypeError):
        return None


class FuncGui(Param):
    """A GUI for Parameters defined by small functions, e.g from numpy"""

    def __init__(self, **kwargs):
        """
        Parameters
        ----------
        **kwargs
            All the parameters fo :method:`~Param.__init__` go here.
        """
        super().__init__(**kwargs)
        self.param_exp = None
        self.param_widget = QLineEdit()
        self.param_widget.setToolTip(
            "Use of functions also allowed "
            "(from already imported modules + numpy as np)\n"
            "Be carefull as everything entered will be executed!"
        )
        self.param_widget.editingFinished.connect(self._get_param)

        self.display_widget = QLabel()
        self.read_param()
        self.init_func_layout()
        self._set_param()
        self.save_param()

    def init_func_layout(self):
        func_layout = QGridLayout()
        label1 = QLabel("Insert Function/Value here")
        label2 = QLabel("Output")
        func_layout.addWidget(label1, 0, 0)
        func_layout.addWidget(label2, 0, 1, 1, 2)
        func_layout.addWidget(self.param_widget, 1, 0)
        func_layout.addWidget(self.display_widget, 1, 1)
        if self.param_unit:
            func_layout.addWidget(QLabel(self.param_unit))
        self.init_ui(func_layout)

    def set_value(self, value):
        self.param_exp = value
        self.param_widget.setText(str(value))
        self.display_widget.setText(str(value)[:20])

    def get_value(self):
        self.param_exp = self.param_widget.text()
        value = _eval_param(self.param_exp)
        self.display_widget.setText(str(value)[:20])

        return value

    def _set_param(self):
        self.check_groupbox_state()
        if self.param_value is not None:
            self.set_value(self.param_exp)

    def set_param(self, value):
        if value is not None:
            self.param_exp = value
        self.param_value = _eval_param(value)
        self._set_param()
        if value is not None:
            self._get_param()

    def read_param(self):
        # Get not only param_value, but also param_exp storing
        # the exact expression which is evaluated
        super().read_param()
        real_value = self.param_value
        self.name = self.name + "_exp"
        super().read_param()
        if self.param_value != "" and self.param_value is not None:
            self.param_exp = self.param_value
        else:
            self.param_exp = real_value
        self.param_value = real_value
        self.name = self.name[:-4]

    def save_param(self):
        super().save_param()
        real_value = self.param_value
        self.name = self.name + "_exp"
        self.param_value = self.param_exp
        super().save_param()
        self.name = self.name[:-4]
        self.param_value = real_value


class BoolGui(Param):
    """A GUI for Boolean-Parameters"""

    def __init__(self, return_integer=False, **kwargs):
        """
        Parameters
        ----------
        return_integer : bool
            Set True to return an integer (0|1) instead of a boolean
            (e.g. useful for QSettings).
        **kwargs
            All the parameters fo :method:`~Param.__init__` go here.
        """
        super().__init__(**kwargs)
        self.return_integer = return_integer
        self.param_widget = QCheckBox()
        self.param_widget.toggled.connect(self._get_param)

        self.read_param()
        self._init_layout()
        self._set_param()
        self.save_param()

    def _init_layout(self):
        layout = QVBoxLayout()
        layout.addWidget(self.param_widget)
        self.init_ui(layout)

    def set_value(self, value):
        self.param_widget.setChecked(bool(value))

    def get_value(self):
        value = self.param_widget.isChecked()
        if self.return_integer:
            value = 1 if value else 0

        return value


class TupleGui(Param):
    """A GUI for Tuple-Parameters"""

    def __init__(self, min_val=-1000.0, max_val=1000.0, step=0.1, **kwargs):
        """
        Parameters
        ----------
        min_val : int | float
            Set the minimumx value, defaults to -100..
        max_val : int | float
            Set the maximum value, defaults to 100..
        step : int | float
            Set the amount, one step takes.
        **kwargs
            All the parameters fo :method:`~Param.__init__` go here.
        """

        super().__init__(**kwargs)

        if step == 1:
            self.param_widget1 = QSpinBox()
            self.param_widget2 = QSpinBox()
            min_val = int(min_val)
            max_val = int(max_val)
        else:
            self.param_widget1 = QDoubleSpinBox()
            self.param_widget2 = QDoubleSpinBox()
            decimals = len(str(step)[str(step).find(".") :]) - 1
            self.param_widget1.setDecimals(decimals)
            self.param_widget2.setDecimals(decimals)

        self._external_set = False

        self.param_widget1.setToolTip(
            f"MinValue = {min_val}\nMaxVal = {max_val}\nStep = {step}\n"
        )
        self.param_widget2.setToolTip(
            f"MinValue = {min_val}\nMaxVal = {max_val}\nStep = {step}\n"
        )

        self.param_widget1.setMinimum(min_val)
        self.param_widget1.setMaximum(max_val)
        self.param_widget1.setSingleStep(step)
        if self.param_unit:
            self.param_widget1.setSuffix(f" {self.param_unit}")
        self.param_widget1.valueChanged.connect(self._get_param)

        self.param_widget2.setMinimum(min_val)
        self.param_widget2.setMaximum(max_val)
        self.param_widget2.setSingleStep(step)
        if self.param_unit:
            self.param_widget2.setSuffix(f" {self.param_unit}")
        self.param_widget2.valueChanged.connect(self._get_param)

        self.read_param()
        self.init_tuple_layout()
        self._set_param()
        self.save_param()

    def init_tuple_layout(self):
        tuple_layout = QHBoxLayout()
        tuple_layout.addWidget(self.param_widget1)
        tuple_layout.addWidget(self.param_widget2)
        self.init_ui(tuple_layout)

    def set_value(self, value):
        # Signal valueChanged is already emitted after first setValue,
        # which leads to second param_value being 0 without being
        # preserved in self.loaded_value
        self._external_set = True
        self.param_widget1.setValue(value[0])
        self.param_widget2.setValue(value[1])
        self._external_set = False

    def _get_param(self):
        if not self._external_set:
            super()._get_param()

    def get_value(self):
        return self.param_widget1.value(), self.param_widget2.value()


class ComboGui(Param):
    """A GUI for a Parameter with limited options"""

    def __init__(self, options, **kwargs):
        """
        Parameters
        ----------
        options : list | dict
            Supply a list or a dictionary with the options to choose from.
            If supplied a dictionary, dictionary-values are
            taken as aliases for the keys.
        **kwargs
            All the parameters fo :method:`~Param.__init__` go here.
        """
        super().__init__(**kwargs)
        self.options = options
        self.param_widget = ComboBox(scrollable=False)
        self.param_widget.activated.connect(self._get_param)
        for option in self.options:
            if isinstance(self.options, dict):
                self.param_widget.addItem(str(self.options[option]))
            else:
                self.param_widget.addItem(str(option))

        self.read_param()
        self._init_layout()
        self._set_param()
        self.save_param()

    def _init_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self.param_widget)
        if self.param_unit is not None:
            layout.addWidget(QLabel(self.param_unit))
        self.init_ui(layout)

    def set_value(self, value):
        if isinstance(self.options, dict):
            self.param_widget.setCurrentText(str(self.options[value]))
        else:
            self.param_widget.setCurrentText(str(value))

    def get_value(self):
        if isinstance(self.options, dict):
            text = [
                key
                for key, value in self.options.items()
                if value == self.param_widget.currentText()
            ][0]
        else:
            text = self.param_widget.currentText()
        try:
            value = literal_eval(text)
        except (SyntaxError, ValueError):
            value = text

        return value


class ListDialog(QDialog):
    def __init__(self, paramw):
        super().__init__(paramw)
        self.paramw = paramw

        self._init_layout()
        self.open()

    def _init_layout(self):
        layout = QVBoxLayout()
        layout.addWidget(EditList(self.paramw.param_value))
        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)
        self.setLayout(layout)

    def closeEvent(self, event):
        self.paramw._set_param()
        self.paramw.save_param()
        event.accept()


class ListGui(Param):
    """A GUI for as list"""

    def __init__(self, value_string_length=30, **kwargs):
        """
        Parameters
        ----------
        value_string_length : int | None
            Set the limit of characters to which the value converted to a
            string will be displayed.
        **kwargs
            All the parameters fo :method:`~Param.__init__` go here.
        """

        super().__init__(**kwargs)
        self.value_string_length = value_string_length
        # Cache param_value to use after
        self.cached_value = None

        self.read_param()
        self._init_layout()
        self._set_param()
        self.save_param()

    def _init_layout(self):
        list_layout = QHBoxLayout()

        self.value_label = QLabel()
        list_layout.addWidget(self.value_label)

        self.param_widget = QPushButton("Edit")
        self.param_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.param_widget.clicked.connect(partial(ListDialog, self))
        list_layout.addWidget(self.param_widget, alignment=Qt.AlignCenter)

        self.init_ui(list_layout)

    def set_value(self, value):
        if value is not None:
            self.cached_value = value
        self.check_groupbox_state()
        if isinstance(value, list):
            if self.param_unit:
                val_str = ", ".join([f"{item} {self.param_unit}" for item in value])
            else:
                val_str = ", ".join([str(item) for item in value])
            if len(val_str) >= self.value_string_length:
                self.value_label.setText(f"{val_str[:self.value_string_length]} ...")
            else:
                self.value_label.setText(val_str)
        else:
            self.value_label.setText("None")

    def get_value(self):
        if self.param_value is None:
            if self.cached_value is not None:
                value = self.cached_value
            else:
                value = list()
            self.value_label.clear()
        else:
            value = self.param_value

        return value


class CheckListDialog(QDialog):
    def __init__(self, paramw):
        super().__init__(paramw)
        self.paramw = paramw

        self._init_layout()
        self.open()

    def _init_layout(self):
        layout = QVBoxLayout()
        layout.addWidget(
            CheckList(
                data=self.paramw.options,
                checked=self.paramw.param_value,
                one_check=self.paramw.one_check,
            )
        )

        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)

    def closeEvent(self, event):
        self.paramw._set_param()
        self.paramw.save_param()
        event.accept()


class CheckListGui(Param):
    """A GUI to select items from a list of options"""

    def __init__(self, options, value_string_length=30, one_check=False, **kwargs):
        """
        Parameters
        ----------
        options : list
            The items from which to choose
        value_string_length : int | None
            Set the limit of characters to which the value converted to a
            string will be displayed.
        one_check : bool
            Set to True, if only one item should be selectable
             (or use ComboGUI).
        **kwargs
            All the parameters fo :method:`~Param.__init__` go here.
        """

        if not isinstance(options, list) or len(options) == 0:
            options = ["Empty"]

        super().__init__(**kwargs)
        self.options = options
        self.value_string_length = value_string_length
        self.one_check = one_check
        # Cache param_value to use after
        self.cached_value = None

        self.read_param()
        self._init_layout()
        self._set_param()
        self.save_param()

    def _init_layout(self):
        check_list_layout = QHBoxLayout()

        self.value_label = QLabel()
        check_list_layout.addWidget(self.value_label)

        self.param_widget = QPushButton("Edit")
        self.param_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.param_widget.clicked.connect(partial(CheckListDialog, self))
        check_list_layout.addWidget(self.param_widget)

        self.init_ui(check_list_layout)

    def set_value(self, value):
        if value is not None:
            self.cached_value = value
        self.check_groupbox_state()
        if isinstance(value, list):
            if self.param_unit:
                val_str = ", ".join([f"{item} {self.param_unit}" for item in value])
            else:
                val_str = ", ".join([str(item) for item in value])
            if len(val_str) >= self.value_string_length:
                self.value_label.setText(f"{val_str[:self.value_string_length]} ...")
            else:
                self.value_label.setText(val_str)
        else:
            self.value_label.setText("None")

    def get_value(self):
        if self.param_value is None:
            if self.cached_value:
                value = self.cached_value
            else:
                value = list()
            self.value_label.clear()
        else:
            value = self.param_value

        return value


class DictDialog(QDialog):
    def __init__(self, paramw):
        super().__init__(paramw)
        self.paramw = paramw

        self._init_layout()
        self.open()

    def _init_layout(self):
        layout = QVBoxLayout()
        layout.addWidget(EditDict(self.paramw.param_value))
        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)
        self.setLayout(layout)

    def closeEvent(self, event):
        self.paramw._set_param()
        self.paramw.save_param()
        event.accept()


class DictGui(Param):
    """A GUI for a dictionary"""

    def __init__(self, value_string_length=30, **kwargs):
        """

        Parameters
        ----------
        value_string_length : int | None
            Set the limit of characters to which the value converted
            to a string will be displayed.
        **kwargs
            All the parameters fo :method:`~Param.__init__` go here.
        """

        super().__init__(**kwargs)
        self.value_string_length = value_string_length
        # Cache param_value to use after setting param_value to None
        # with GroupBox-Checkbox
        self.cached_value = None

        self.read_param()
        self._init_layout()
        self._set_param()
        self.save_param()

    def _init_layout(self):
        dict_layout = QHBoxLayout()

        self.value_label = QLabel()
        dict_layout.addWidget(self.value_label)

        self.param_widget = QPushButton("Edit")
        self.param_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.param_widget.clicked.connect(partial(DictDialog, self))
        dict_layout.addWidget(self.param_widget)

        self.init_ui(dict_layout)

    # ToDo: improve None-handling, maybe generalize
    #  (sometimes error when value=float, probably nan)
    def set_value(self, value):
        if value is not None:
            self.cached_value = value
        self.check_groupbox_state()
        if isinstance(value, dict):
            if self.param_unit:
                val_str = ", ".join(
                    [
                        f"{k} {self.param_unit}: {v} {self.param_unit}"
                        for k, v in value.items()
                    ]
                )
            else:
                val_str = ", ".join([f"{k}: {v}" for k, v in value.items()])
            if len(val_str) > self.value_string_length:
                self.value_label.setText(f"{val_str[:self.value_string_length]} ...")
            else:
                self.value_label.setText(val_str)
        else:
            self.value_label.setText("None")

    def get_value(self):
        if self.param_value is None:
            if self.cached_value:
                value = self.cached_value
            else:
                value = dict()
            self.value_label.clear()
        else:
            value = self.param_value

        return value


class SliderGui(Param):
    """A GUI to show a slider for Int/Float-Parameters"""

    def __init__(self, min_val=0, max_val=100, step=1, tracking=True, **kwargs):
        """
        Parameters
        ----------
        min_val : int | float
            Set the minimumx value, defaults to 0.
        max_val : int | float
            Set the maximum value, defaults to 100..
        step : int | float
            Set the step-size, defaults to 1.
        tracking : bool
            Set True if values should be updated constantly while the slider
            is dragged (can cause crashes when heavyweight functions are
            connected to the ParamChanged-Signal).
        **kwargs
            All the parameters fo :method:`~Param.__init__` go here.
        """
        super().__init__(**kwargs)
        self.min_val = min_val
        self.max_val = max_val
        self.param_widget = QSlider()
        self.param_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.decimal_count = max(
            [
                len(str(value)[str(value).find(".") :]) - 1
                for value in [min_val, max_val, step]
            ]
        )
        if self.decimal_count > 0:
            self.param_widget.setMinimum(int(self.min_val * 10**self.decimal_count))
            self.param_widget.setMaximum(int(self.max_val * 10**self.decimal_count))
        else:
            self.param_widget.setMinimum(self.min_val)
            self.param_widget.setMaximum(self.max_val)
        self.param_widget.setSingleStep(int(step))
        self.param_widget.setOrientation(Qt.Horizontal)
        # Only change value when slider is released
        self.param_widget.setTracking(tracking)
        self.param_widget.setToolTip(
            f"MinValue = {min_val}\nMaxValue = {max_val}\nStep = {step}"
        )
        self.param_widget.valueChanged.connect(self._get_param)

        self.display_widget = QLineEdit()
        self.display_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.display_widget.setAlignment(Qt.AlignRight)
        self.display_widget.editingFinished.connect(self.display_edited)

        self.read_param()
        self.init_slider_ui()
        self._set_param()
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
            new_value = None
        if new_value:
            self.param_value = new_value
            self.param_widget.setValue(int(new_value * 10**self.decimal_count))

    def set_value(self, value):
        self.check_groupbox_state()
        if value is not None:
            if self.decimal_count > 0:
                self.param_widget.setValue(int(value * 10**self.decimal_count))
            else:
                self.param_widget.setValue(value)
            self.display_widget.setText(str(value))

    def get_value(self):
        value = self.param_widget.value()
        if self.decimal_count > 0:
            value /= 10**self.decimal_count
        self.display_widget.setText(str(value))

        return value


class MultiTypeGui(Param):
    """A GUI which accepts multiple types of values in a single LineEdit"""

    def __init__(self, type_selection=False, types=None, type_kwargs=None, **kwargs):
        """
        Parameters
        ----------
        type_selection : bool
            If True, the use can choose in a QComboBox which type they want
            to enter and then use the appropriate GUI.
        types : list of str | None
            If type_selection is True, the type-selection will be limited
            to the given types (type-name as string).
        type_kwargs : dict | None
            Specify keyword-arguments as a dictionary for the different GUIs
            (look into their documentation),
            the key is the name of the GUI (e.g. IntGui).
        **kwargs
            All the parameters fo :method:`~Param.__init__` go here.
        """
        super().__init__(**kwargs)
        self.type_selection = type_selection
        self.types = types or ["int", "float", "bool", "str", "list", "dict", "tuple"]
        self.type_kwargs = type_kwargs or dict()

        # A dictionary to map possible types with their GUI
        self.gui_types = {
            "int": "IntGui",
            "float": "FloatGui",
            "bool": "BoolGui",
            "str": "StringGui",
            "list": "ListGui",
            "dict": "DictGui",
            "tuple": "TupleGui",
        }

        if self.type_selection:
            self.type_cmbx = QComboBox()
            self.type_cmbx.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            self.type_cmbx.addItems(self.types)
            self.type_cmbx.activated.connect(self.change_type)
        else:
            self.param_widget = QLineEdit()
            self.param_widget.textEdited.connect(self._get_param)
            self.type_display = QLabel()

        self.read_param()

        # Get current type (NoneType not allowed)
        self.param_type = type(self.param_value).__name__
        if self.param_type == "NoneType":
            self.param_type = self.types[0]
        if self.type_selection:
            self.type_cmbx.setCurrentText(self.param_type)

        self._init_layout()
        self._set_param()
        self.save_param()

    def add_type_gui(self):
        gui_name = self.gui_types[self.param_type]

        # Load specifc keyword-arguments if given
        if gui_name in self.type_kwargs:
            kwargs = self.type_kwargs[gui_name]
        else:
            kwargs = dict()

        # Set standard parameter-keyword-arguments as given to MultiTypeGui
        kwargs["data"] = self.data
        kwargs["name"] = self.name
        kwargs["alias"] = ""
        kwargs["default"] = self.default
        kwargs["groupbox_layout"] = False
        kwargs["none_select"] = False
        kwargs["description"] = self.description
        kwargs["param_unit"] = self.param_unit

        self.param_widget = globals()[gui_name](**kwargs)
        self.param_widget.param_value = self.param_value
        self.param_widget._get_param()
        self.param_widget._set_param()
        self.type_layout.addWidget(self.param_widget)

    def change_type(self, type_idx):
        # Set Param-Value to None to avoid conflicts
        # whith values from other types
        self.param_value = None
        self.save_param()

        old_widget = self.type_layout.itemAt(1)
        self.type_layout.removeItem(old_widget)
        old_widget.widget().deleteLater()
        del old_widget, self.param_widget

        self.param_type = self.types[type_idx]

        self.add_type_gui()

    def _init_layout(self):
        if self.type_selection:
            self.type_layout = QHBoxLayout()
            self.type_layout.addWidget(self.type_cmbx)
            self.add_type_gui()
            self.init_ui(self.type_layout)
        else:
            type_layout = QHBoxLayout()
            type_layout.addWidget(self.param_widget)
            type_layout.addWidget(self.type_display)
            self.init_ui(type_layout)

    def set_value(self, value):
        self.check_groupbox_state()
        if self.type_selection:
            self.param_widget.param_value = value
            self.param_widget._set_param()
        elif value is not None:
            self.param_widget.setText(str(value))
            self.type_display.setText(f"Type: {type(value).__name__}")

    def get_value(self):
        if self.type_selection:
            self.param_widget._get_param()
            value = self.param_widget.param_value
        else:
            text = self.param_widget.text()
            try:
                value = literal_eval(text)
                self.param_type = type(value).__name__
            except ValueError:
                value = text
                self.param_type = "str"
            except SyntaxError:
                value = None
                self.param_type = "error"
            self.type_display.setText(f"Type: {self.param_type}")
            self.save_param()

        return value


class LabelPicker(mne.viz.Brain):
    def __init__(self, paramdlg, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            # Backwards compatibility mne==0.24
            kwargs.pop("block")
            super().__init__(*args, **kwargs)
        self.paramdlg = paramdlg
        self.paramw = paramdlg.paramw

        self._shown_labels = list()

        self._set_annotations()
        self._init_picking()
        self.add_text(0, 0.9, "Pick labels", "title", font_size=14)

    def _set_annotations(self):
        fsmri = self.paramdlg._fsmri
        parcellation = self.paramdlg._parcellation
        self.clear_glyphs()
        self.remove_labels()
        self.remove_annotations()
        self.add_annotation(parcellation, color="w", alpha=0.75)

        for parc in [parcellation, "Other"]:
            if parc in fsmri.labels:
                labels = fsmri.labels[parc]
                for hemi in self._hemis:
                    hemi_labels = [lb for lb in labels if lb.hemi == hemi]
                    self._vertex_to_label_id[hemi] = np.full(
                        self.geo[hemi].coords.shape[0], -1
                    )
                    self._annotation_labels[hemi] = hemi_labels
                    for idx, label in enumerate(hemi_labels):
                        self._vertex_to_label_id[hemi][label.vertices] = idx

    def _init_picking(self):
        self._mouse_no_mvt = -1
        add_obs = self._renderer.plotter.iren.add_observer
        add_obs(vtkCommand.RenderEvent, self._on_mouse_move)
        add_obs(vtkCommand.LeftButtonPressEvent, self._on_button_press)
        add_obs(vtkCommand.EndInteractionEvent, self._on_button_release)
        self._renderer.plotter.picker = vtkCellPicker()
        self._renderer.plotter.picker.AddObserver(
            vtkCommand.EndPickEvent, self._label_picked
        )

    def _label_picked(self, vtk_picker, _):
        cell_id = vtk_picker.GetCellId()
        mesh = vtk_picker.GetDataSet()
        if mesh is not None:
            hemi = mesh._hemi
            if mesh is None or cell_id == -1 or not self._mouse_no_mvt:
                return  # don't pick
            pos = np.array(vtk_picker.GetPickPosition())
            vtk_cell = mesh.GetCell(cell_id)
            cell = [
                vtk_cell.GetPointId(point_id)
                for point_id in range(vtk_cell.GetNumberOfPoints())
            ]
            vertices = mesh.points[cell]
            idx = np.argmin(abs(vertices - pos), axis=0)
            vertex_id = cell[idx[0]]

            label_id = self._vertex_to_label_id[hemi][vertex_id]
            label = self._annotation_labels[hemi][label_id]

            if label.name in self.paramdlg._selected_labels:
                self._remove_label_name(label.name, hemi)
                self.paramdlg._selected_labels.remove(label.name)
            else:
                self._add_label_name(label.name, hemi, label)
                self.paramdlg._selected_labels.append(label.name)
            self.paramdlg.label_list.content_changed()

    def _add_label_name(self, label_name, hemi, label=None):
        if label is None:
            for lb in self._annotation_labels[hemi]:
                if lb.name == label_name:
                    label = lb
                    break
        if label is not None:
            self.add_label(label, borders=False, reset_camera=False)
            self._shown_labels.append(label_name)

    def _remove_label_name(self, label_name, hemi):
        self._layered_meshes[hemi].remove_overlay(label_name)
        self._shown_labels.remove(label_name)
        self._renderer._update()

    def closeEvent(self, event):
        self.paramdlg._label_picker = None
        super().closeEvent(event)


class LabelDialog(SimpleDialog):
    def __init__(self, paramw):
        self.main_widget = QWidget()
        super().__init__(
            self.main_widget,
            parent=paramw,
            title="Choose a label!",
            window_title="Label Picker",
            modal=False,
        )
        self.paramw = paramw
        self.ct = paramw.data
        self.params = self.ct.pr.parameters[self.ct.pr.p_preset]
        self.param_value = paramw.param_value

        self._label_picker = None
        self._fsmri = None
        self._parcellation = None
        self._all_label_names = list()
        self._selected_labels = list()

        self.resize(400, 800)
        center(self)

        self._init_layout()
        self.open()

    def _init_layout(self):
        layout = QVBoxLayout(self.main_widget)

        self.fsmri_cmbx = QComboBox()
        self.fsmri_cmbx.addItems(self.ct.pr.all_fsmri)
        self.fsmri_cmbx.activated.connect(self._subject_changed)
        layout.addWidget(self.fsmri_cmbx)

        self.parcellation_cmbx = QComboBox()
        self.parcellation_cmbx.activated.connect(self._parc_changed)
        layout.addWidget(self.parcellation_cmbx)

        self.label_list = CheckList(
            data=self._all_label_names,
            checked=self._selected_labels,
            ui_buttons=True,
            ui_button_pos="bottom",
        )
        self.label_list.checkedChanged.connect(self._labels_changed)
        layout.addWidget(self.label_list)

        # ToDo: fix Brain-Picker (errors and somehow all labels are selected)
        # slider_kwargs = {'max_val': 360, 'tracking': False}
        # self.elevation_slider = SliderGui(data=self.paramw.data,
        #                                   name='stc_elevation',
        #                                   **slider_kwargs)
        # self.elevation_slider.paramChanged.connect(self._slider_changed)
        # layout.addWidget(self.elevation_slider)
        #
        # self.roll_slider = SliderGui(data=self.paramw.data,
        #                              name='stc_roll',
        #                              **slider_kwargs)
        # self.roll_slider.paramChanged.connect(self._slider_changed)
        # layout.addWidget(self.roll_slider)
        #
        # self.azimuth_slider = SliderGui(data=self.paramw.data,
        #                                 name='stc_azimuth',
        #                                 **slider_kwargs)
        # self.azimuth_slider.paramChanged.connect(self._slider_changed)
        # layout.addWidget(self.azimuth_slider)
        #
        # choose_bt = QPushButton('Choose Labels')
        # choose_bt.clicked.connect(self._open_label_picker)
        # layout.addWidget(choose_bt)

        # Initialize with first items
        self._subject_changed()
        self._parc_changed()

    def _subject_changed(self):
        self._fsmri = FSMRI(self.fsmri_cmbx.currentText(), self.ct, load_labels=True)

        self.parcellation_cmbx.clear()
        self.parcellation_cmbx.addItems(self._fsmri.parcellations)
        self._parc_changed()

    def _parc_changed(self):
        # Keep reference for inplace change
        self._all_label_names.clear()
        self._selected_labels.clear()

        # Add single labels
        self._all_label_names += [lb.name for lb in self._fsmri.labels["Other"]]

        # Add parcellation labels
        self._parcellation = self.parcellation_cmbx.currentText()
        if self._parcellation in self._fsmri.labels:
            self._all_label_names += [
                lb.name for lb in self._fsmri.labels[self._parcellation]
            ]

        # get selected
        self._selected_labels += [
            lb for lb in self.paramw.param_value if lb in self._all_label_names
        ]
        self.label_list.content_changed()

        if self._label_picker is not None:
            self._label_picker._set_annotations()

    def _labels_changed(self, labels):
        if self._label_picker is not None:
            shown_labels = self._label_picker._shown_labels
            for add_name in [lb for lb in labels if lb not in shown_labels]:
                hemi = add_name[-2:]
                self._label_picker._add_label_name(add_name, hemi)
            for remove_name in [lb for lb in shown_labels if lb not in labels]:
                hemi = remove_name[-2:]
                self._label_picker._remove_label_name(remove_name, hemi)

    def _slider_changed(self, _):
        if self._label_picker is not None:
            roll = self.roll_slider.param_value
            elevation = self.elevation_slider.param_value
            azimuth = self.azimuth_slider.param_value
            for row, col in [(0, 0), (0, 1), (1, 0), (1, 1)]:
                self._label_picker.show_view(
                    roll=roll, elevation=elevation, azimuth=azimuth, row=row, col=col
                )

    def _open_label_picker(self):
        background = self.params["stc_background"]

        self._label_picker = LabelPicker(
            self,
            self._fsmri.name,
            hemi="split",
            views=["lat", "med"],
            surf="inflated",
            title="Pick labels",
            subjects_dir=self.ct.subjects_dir,
            block=False,
            background=background,
        )
        self._slider_changed(None)

    def closeEvent(self, event):
        event.accept()
        self.paramw.param_value = self._selected_labels
        self.paramw._get_param()
        self.paramw._set_param()
        if self._label_picker is not None:
            if self._label_picker.plotter is not None:
                self._label_picker.plotter.close()
        # ToDo: Update slider across all instances


class LabelGui(Param):
    """This GUI lets the user pick labels from a brain."""

    def __init__(self, value_string_length=30, **kwargs):
        """
        Parameters
        ----------
        value_string_length : int | None
            Set the limit of characters to which the value converted to a
            string will be displayed.
        **kwargs
            All the parameters fo :method:`~Param.__init__` go here.
        """

        super().__init__(**kwargs)
        self.value_string_length = value_string_length
        if not isinstance(self.data, Controller):
            raise RuntimeError(
                "LabelGui can only used with an instance of "
                "Controller passed as data."
            )
        self.read_param()
        self._init_layout()
        self._set_param()
        self.save_param()

    def _init_layout(self):
        check_list_layout = QHBoxLayout()

        self.value_label = QLabel()
        check_list_layout.addWidget(self.value_label)

        self.param_widget = QPushButton("Edit")
        self.param_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.param_widget.clicked.connect(partial(LabelDialog, self))
        check_list_layout.addWidget(self.param_widget)

        self.init_ui(check_list_layout)

    def set_value(self, value):
        if value is not None:
            self.cached_value = value
        self.check_groupbox_state()
        if isinstance(value, list):
            if self.param_unit:
                val_str = ", ".join([f"{item}" for item in value])
            else:
                val_str = ", ".join([str(item) for item in value])
            if len(val_str) >= self.value_string_length:
                self.value_label.setText(f"{val_str[:self.value_string_length]} ...")
            else:
                self.value_label.setText(val_str)
        else:
            self.value_label.setText("None")

    def get_value(self):
        if self.param_value is None:
            if self.cached_value:
                value = self.cached_value
            else:
                value = list()
            self.value_label.clear()
        else:
            value = self.param_value

        return value


class ColorGui(Param):
    """A GUI to pick a color and returns a dictionary with HexRGBA-Strings."""

    def __init__(self, keys, **kwargs):
        """
        Parameters
        ----------
        keys : dict | str | None
            If you supply a dictionary with keys, you can set a color
            for each key. If you supply the string name of another parameter
            (which must return an iterable!), the values from there are taken.
        **kwargs
            All the parameters for :method:`Param.__init__` go here.
        """

        super().__init__(**kwargs)

        if isinstance(keys, str):
            self.keys = self._read_data(keys)
        else:
            self.keys = keys

        self._cached_value = self.param_value

        self.read_param()
        self._init_layout()
        self._set_param()
        self.save_param()

    def _init_layout(self):
        layout = QHBoxLayout()
        self.select_widget = QComboBox()
        self.select_widget.setEditable(True)
        self.select_widget.addItems([str(k) for k in self.keys])
        self.select_widget.activated.connect(self._change_display_color)
        layout.addWidget(self.select_widget)
        self.display_widget = QLabel()
        self.display_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        layout.addWidget(self.display_widget)
        self.param_widget = QPushButton("Pick Color")
        self.param_widget.clicked.connect(self._pick_color)
        layout.addWidget(self.param_widget)
        self.init_ui(layout)

    def _change_display_color(self):
        key = self.select_widget.currentText()
        if key in self._cached_value:
            color = _get_color(self._cached_value[key])
            pixmap = QPixmap(20, 20)
            pixmap.fill(color)
            self.display_widget.setPixmap(pixmap)
        else:
            self.display_widget.setText("None")

    def set_value(self, value):
        self._cached_value = value
        self.keys = value.keys()
        self._change_display_color()

    def get_value(self):
        return self._cached_value

    def _pick_color(self):
        key = self.select_widget.currentText()
        if key in self._cached_value:
            previous_color = _get_color(self._cached_value[key])
            color = QColorDialog.getColor(
                initial=previous_color,
                parent=self,
                title=f"Pick a color for {self.name}",
            )
        else:
            # blocking
            color = QColorDialog.getColor(
                parent=self, title=f"Pick a color for {self.name}"
            )
        self._cached_value[key] = color.name()
        self._change_display_color()
        self._set_param()
        self._get_param()


# Todo: Ordering Parameters in Tabs and add Find-Command
class ResetDialog(QDialog):
    def __init__(self, p_dock):
        super().__init__(p_dock)
        self.pd = p_dock
        self.selected_params = list()

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(
            CheckList(
                list(self.pd.ct.pr.parameters[self.pd.ct.pr.p_preset].keys()),
                self.selected_params,
                title="Select the Parameters to reset",
            )
        )
        reset_bt = QPushButton("Reset")
        reset_bt.clicked.connect(self.reset_params)
        layout.addWidget(reset_bt)

        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)

    def reset_params(self):
        for name in self.selected_params:
            self.pd.ct.pr.load_default_param(name)
            print(f"Reset {name}")
        WorkerDialog(self, self.pd.ct.pr.save, title="Saving project...", blocking=True)
        self.pd.update_all_param_guis()
        self.close()


class CopyPDialog(QDialog):
    def __init__(self, p_dock):
        super().__init__(p_dock)
        self.pd = p_dock
        self.p = p_dock.ct.pr.parameters
        self.selected_from = None
        self.selected_to = list()
        self.selected_ps = list()

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        list_layout = QHBoxLayout()
        copy_from = SimpleList(list(self.p.keys()))
        copy_from.currentChanged.connect(self.from_selected)
        list_layout.addWidget(copy_from)

        self.copy_to = CheckList(checked=self.selected_to)
        list_layout.addWidget(self.copy_to)

        self.copy_ps = CheckList(checked=self.selected_ps)
        list_layout.addWidget(self.copy_ps)

        layout.addLayout(list_layout)

        bt_layout = QHBoxLayout()

        copy_bt = QPushButton("Copy")
        copy_bt.clicked.connect(self.copy_parameters)
        bt_layout.addWidget(copy_bt)

        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        bt_layout.addWidget(close_bt)

        layout.addLayout(bt_layout)

        self.setLayout(layout)

    def from_selected(self, current):
        self.selected_from = current
        self.copy_to.replace_data([pp for pp in self.p.keys() if pp != current])
        self.copy_ps.replace_data([p for p in self.p[current]])

    def copy_parameters(self):
        if len(self.selected_to) > 0:
            for p_preset in self.selected_to:
                for parameter in self.selected_ps:
                    self.p[p_preset][parameter] = self.p[self.selected_from][parameter]

            WorkerDialog(
                self, self.pd.ct.pr.save, title="Saving project...", blocking=True
            )
            self.pd.update_all_param_guis()
            self.close()


class RemovePPresetDlg(CheckListDlg):
    def __init__(self, parent):
        self.parent = parent
        self.preset_list = [p for p in self.parent.ct.pr.parameters if p != "Default"]
        self.rm_list = []

        super().__init__(parent, self.preset_list, self.rm_list)

        self.do_bt.setText("Remove Parameter-Preset")
        self.do_bt.clicked.connect(self.remove_selected)

        self.open()

    def remove_selected(self):
        for p_preset in self.rm_list:
            self.preset_list.remove(p_preset)
            self.lm.layoutChanged.emit()
            # Remove from Parameters
            self.parent.ct.pr.parameters.pop(p_preset)
            self.parent.update_ppreset_cmbx()

        # If current Parameter-Preset was deleted
        if self.parent.ct.pr.p_preset not in self.parent.ct.pr.parameters:
            self.parent.ct.pr.p_preset = list(self.parent.ct.pr.parameters.keys())[0]
            self.parent.update_all_param_guis()

        self.close()


class ParametersDock(QDockWidget):
    def __init__(self, main_win):
        super().__init__("Parameters", main_win)
        self.mw = main_win
        self.ct = main_win.ct
        self.setAllowedAreas(Qt.RightDockWidgetArea)
        self.main_widget = QWidget()
        self.param_guis = {}

        self.dropgroup_params()
        self.init_ui()

    def dropgroup_params(self):
        # Create a set of all unique parameters used by functions
        # in selected_modules
        sel_pdfuncs = self.ct.pd_funcs.loc[
            self.ct.pd_funcs["module"].isin(self.ct.get_setting("selected_modules"))
        ]
        # Remove rows with NaN in func_args
        sel_pdfuncs = sel_pdfuncs.loc[sel_pdfuncs["func_args"].notna()]
        all_used_params_str = ",".join(sel_pdfuncs["func_args"])
        # Make sure there are no spaces left
        all_used_params_str = all_used_params_str.replace(" ", "")
        all_used_params = set(all_used_params_str.split(","))
        drop_idx_list = list()
        self.cleaned_pd_params = self.ct.pd_params.copy()
        for param in self.cleaned_pd_params.index:
            if param in all_used_params:
                # Group-Name (if not given, set to 'Various')
                group_name = self.cleaned_pd_params.loc[param, "group"]
                if pd.isna(group_name):
                    self.cleaned_pd_params.loc[param, "group"] = "Various"
            else:
                # Drop Parameters which aren't used by functions
                drop_idx_list.append(param)
        self.cleaned_pd_params.drop(index=drop_idx_list, inplace=True)

    def init_ui(self):
        self.general_layout = QVBoxLayout()

        # Add Parameter-Preset-ComboBox
        title_layouts = QVBoxLayout()
        title_layout1 = QHBoxLayout()
        p_preset_l = QLabel("Parameter-Presets: ")
        title_layout1.addWidget(p_preset_l)
        self.p_preset_cmbx = QComboBox()
        self.p_preset_cmbx.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.p_preset_cmbx.activated.connect(self.p_preset_changed)
        self.update_ppreset_cmbx()
        title_layout1.addWidget(self.p_preset_cmbx)

        add_bt = QPushButton(icon=get_std_icon("SP_FileDialogNewFolder"))
        add_bt.clicked.connect(self.add_p_preset)
        title_layout1.addWidget(add_bt)

        rm_bt = QPushButton(icon=get_std_icon("SP_DialogDiscardButton"))
        rm_bt.clicked.connect(partial(RemovePPresetDlg, self))
        title_layout1.addWidget(rm_bt)

        title_layouts.addLayout(title_layout1)

        title_layout2 = QHBoxLayout()
        copy_bt = QPushButton("Copy")
        copy_bt.setFont(QFont(QS().value("app_font"), 16))
        copy_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        copy_bt.clicked.connect(partial(CopyPDialog, self))
        title_layout2.addWidget(copy_bt)

        reset_bt = QPushButton("Reset")
        reset_bt.setFont(QFont(QS().value("app_font"), 16))
        reset_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        reset_bt.clicked.connect(partial(ResetDialog, self))
        title_layout2.addWidget(reset_bt)

        reset_all_bt = QPushButton("Reset All")
        reset_all_bt.setFont(QFont(QS().value("app_font"), 16))
        reset_all_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        reset_all_bt.clicked.connect(self.reset_all_parameters)
        title_layout2.addWidget(reset_all_bt)

        title_layouts.addLayout(title_layout2)
        self.general_layout.addLayout(title_layouts)

        self.add_param_guis()

        self.main_widget.setLayout(self.general_layout)
        self.setWidget(self.main_widget)

    def add_param_guis(self):
        # Create Tab-Widget for Parameters, grouped by group
        self.tab_param_widget = QTabWidget()

        grouped_params = self.cleaned_pd_params.groupby("group", sort=False)

        for group_name, group in grouped_params:
            layout = QVBoxLayout()
            tab = QScrollArea()
            child_w = QWidget()
            for idx, parameter in group.iterrows():
                # Get Parameters for Gui-Call
                if pd.notna(parameter["alias"]):
                    alias = parameter["alias"]
                else:
                    alias = idx
                if pd.notna(parameter["gui_type"]):
                    gui_name = parameter["gui_type"]
                else:
                    gui_name = "FuncGui"
                try:
                    default = literal_eval(parameter["default"])
                except (SyntaxError, ValueError):
                    if gui_name == "FuncGui":
                        default = _eval_param(parameter["default"])
                    else:
                        default = parameter["default"]
                if pd.notna(parameter["description"]):
                    description = parameter["description"]
                else:
                    description = ""
                if pd.notna(parameter["unit"]):
                    unit = parameter["unit"]
                else:
                    unit = None
                try:
                    gui_args = literal_eval(parameter["gui_args"])
                except (SyntaxError, ValueError):
                    gui_args = {}

                try:
                    self.param_guis[idx] = globals()[gui_name](
                        data=self.ct,
                        name=idx,
                        alias=alias,
                        default=default,
                        description=description,
                        param_unit=unit,
                        **gui_args,
                    )
                except Exception:
                    err_tuple = get_exception_tuple()
                    raise RuntimeError(
                        f'Initialization of Parameter-Widget "{idx}" '
                        f"with value={default} "
                        f"failed:\n"
                        f"{err_tuple[1]}"
                    )

                layout.addWidget(self.param_guis[idx])

            child_w.setLayout(layout)
            tab.setWidget(child_w)
            self.tab_param_widget.addTab(tab, group_name)

        # Set Layout of QWidget (the class itself)
        self.general_layout.addWidget(self.tab_param_widget)

    def update_ppreset_cmbx(self):
        self.p_preset_cmbx.clear()
        for p_preset in self.ct.pr.parameters.keys():
            self.p_preset_cmbx.addItem(p_preset)
        if self.ct.pr.p_preset in self.ct.pr.parameters.keys():
            self.p_preset_cmbx.setCurrentText(self.ct.pr.p_preset)
        else:
            self.p_preset_cmbx.setCurrentText(list(self.ct.pr.parameters.keys())[0])

    def p_preset_changed(self, idx):
        self.ct.pr.p_preset = self.p_preset_cmbx.itemText(idx)
        self.update_all_param_guis()

    def add_p_preset(self):
        preset_name = get_user_input_string(
            "Enter a name for a new Parameter-Preset:", "Add Parameter-Preset"
        )
        if preset_name is not None:
            self.ct.pr.p_preset = preset_name
            self.ct.pr.load_default_parameters()
            self.p_preset_cmbx.addItem(preset_name)
            self.p_preset_cmbx.setCurrentText(preset_name)

    def redraw_param_widgets(self):
        self.general_layout.removeWidget(self.tab_param_widget)
        self.tab_param_widget.close()
        del self.tab_param_widget
        self.dropgroup_params()
        self.add_param_guis()
        self.update_ppreset_cmbx()

    def update_all_param_guis(self):
        for gui_name in self.param_guis:
            param_gui = self.param_guis[gui_name]
            param_gui.read_param()
            param_gui._set_param()

    def reset_all_parameters(self):
        msgbox = QMessageBox.question(
            self,
            "Reset all Parameters?",
            "Do you really want to reset all " "parameters to their default?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if msgbox == QMessageBox.Yes:
            self.ct.pr.load_default_parameters()
            self.update_all_param_guis()


class SettingsDlg(QDialog):
    def __init__(self, parent_widget, controller):
        super().__init__(parent_widget)
        self.ct = controller

        self.settings_items = {
            "app_style": {
                "gui_type": "ComboGui",
                "data_type": "QSettings",
                "gui_kwargs": {
                    "alias": "Application Style",
                    "description": "Changes the application style "
                    "(Restart required).",
                    "options": ["light", "dark", "auto"],
                },
            },
            "app_font": {
                "gui_type": "ComboGui",
                "data_type": "QSettings",
                "gui_kwargs": {
                    "alias": "Application Font",
                    "description": "Changes default application font "
                    "(Restart required).",
                    "options": QFontDatabase().families(QFontDatabase.Latin),
                },
            },
            "app_font_size": {
                "gui_type": "IntGui",
                "data_type": "QSettings",
                "gui_kwargs": {
                    "alias": "Font Size",
                    "description": "Changes default application font-size "
                    "(Restart required).",
                    "min_val": 5,
                    "max_val": 20,
                },
            },
            "img_format": {
                "gui_type": "ComboGui",
                "data_type": "Settings",
                "gui_kwargs": {
                    "alias": "Image Format",
                    "description": "Choose the image format for plots.",
                    "options": [".png", ".jpg", ".tiff"],
                },
            },
            "dpi": {
                "gui_type": "IntGui",
                "data_type": "Settings",
                "gui_kwargs": {
                    "alias": "DPI",
                    "description": "Set dpi for saved plots.",
                    "min_val": 10,
                    "max_val": 5000,
                },
            },
            "enable_cuda": {
                "gui_type": "BoolGui",
                "data_type": "QSettings",
                "gui_kwargs": {
                    "alias": "Enable CUDA",
                    "description": "Enable for CUDA support "
                    "(system has to be setup for cuda "
                    "as in https://mne.tools/stable/install/"
                    "advanced.html#gpu-acceleration-with-cuda)",
                    "return_integer": True,
                },
            },
            "save_ram": {
                "gui_type": "BoolGui",
                "data_type": "QSettings",
                "gui_kwargs": {
                    "alias": "Save RAM",
                    "description": "Set to True on low RAM-Machines to avoid"
                    " the process to be killed by the OS due "
                    "to low Memory (with leaving it off, "
                    "the pipeline goes a bit faster, because "
                    "the data can be saved in memory).",
                    "return_integer": True,
                },
            },
            "fs_path": {
                "gui_type": "StringGui",
                "data_type": "QSettings",
                "gui_kwargs": {
                    "alias": "FREESURFER_HOME-Path",
                    "description": 'Set the Path to the "freesurfer"-directory'
                    " of your Freesurfer-Installation "
                    "(for Windows to the LINUX-Path of the "
                    "Freesurfer-Installation in "
                    "Windows-Subsystem for Linux(WSL))",
                    "none_select": True,
                },
            },
            "mne_path": {
                "gui_type": "StringGui",
                "data_type": "QSettings",
                "gui_kwargs": {
                    "alias": "MNE-WSL-Path",
                    "description": "Set the LINUX-Path to the mne-environment "
                    "(e.g ...anaconda3/envs/mne) in "
                    "Windows-Subsystem for Linux(WSL))",
                    "none_select": True,
                },
            },
        }

        if not iswin:
            self.settings_items.pop("mne_path")

        self.init_ui()
        self.open()

    def init_ui(self):
        layout = QVBoxLayout()

        for setting in self.settings_items:
            gui_handle = globals()[self.settings_items[setting]["gui_type"]]
            data_type = self.settings_items[setting]["data_type"]
            gui_kwargs = self.settings_items[setting]["gui_kwargs"]
            if data_type == "QSettings":
                gui_kwargs["data"] = QS()
                gui_kwargs["default"] = self.ct.default_settings["qsettings"][setting]
            elif data_type == "Controller":
                gui_kwargs["data"] = self.mw.ct
                gui_kwargs["default"] = self.ct.pd_params.loc[setting, "default"]
            else:
                gui_kwargs["data"] = self.ct.settings
                gui_kwargs["default"] = self.ct.default_settings["settings"][setting]
            gui_kwargs["name"] = setting
            layout.addWidget(gui_handle(**gui_kwargs))

        close_bt = QPushButton("Close")
        close_bt.clicked.connect(self.close)
        layout.addWidget(close_bt)

        self.setLayout(layout)
